import boto3
import os
import logging
from datetime import datetime, timedelta

# set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# aws clients
ec2 = boto3.client('ec2')
sns = boto3.client('sns')

# environment variables
SNS_TOPIC = os.environ.get('sns_topic')
RETENTION_DAYS = int(os.environ.get("retention_days", 7))


def get_instance_ids():
    instance_ids = []
    logger.info("Fetching instances with tag 'Backup: True'")
    paginator = ec2.get_paginator('describe_instances')

    try:
        for page in paginator.paginate(
            Filters=[{'Name': 'tag:Backup', 'Values': ['True']}]
        ):
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    instance_ids.append(instance['InstanceId'])
        
        logger.info(f"Found {len(instance_ids)} instances to backup.")
        return instance_ids
    except Exception as e:
        logger.error(f"Error fetching instance IDs: {str(e)}")
        return []


def create_ami(instance_id):
    try:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
        expiry_date = (datetime.utcnow() + timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d")

        logger.info(f"Creating AMI for instance {instance_id}...")
        response = ec2.create_image(
            InstanceId=instance_id,
            Name=f"Backup-{instance_id}-{timestamp}",
            NoReboot=True
        )

        image_id = response['ImageId']

        ec2.create_tags(
            Resources=[image_id],
            Tags=[
                {'Key': 'CreatedBy', 'Value': 'Lambda'},
                {'Key': 'Backup', 'Value': 'True'},
                {'Key': 'InstanceId', 'Value': instance_id},
                {'Key': 'DeleteAfter', 'Value': expiry_date}
            ]
        )

        logger.info(f"Successfully created AMI {image_id} for {instance_id}. Expiry set to {expiry_date}")
        return {"instance": instance_id, "status": "success", "image_id": image_id}

    except Exception as e:
        logger.error(f"AMI creation failed for {instance_id}: {str(e)}")
        return {"instance": instance_id, "status": "failed", "error": str(e)}


def delete_expired_amis():
    deleted = []
    today = datetime.utcnow().strftime("%Y-%m-%d")
    logger.info("Checking for expired AMIs...")

    try:
        images = ec2.describe_images(Owners=['self'])['Images']

        for image in images:
            tags = {tag['Key']: tag['Value'] for tag in image.get('Tags', [])}

            if tags.get('Backup') != 'True' or not tags.get('DeleteAfter'):
                continue

            if tags.get('DeleteAfter') <= today:
                image_id = image['ImageId']
                logger.info(f"AMI {image_id} has expired. Starting cleanup.")

                try:
                    # Deregister AMI
                    ec2.deregister_image(ImageId=image_id)
                    
                    # Delete associated snapshots
                    for bd in image.get('BlockDeviceMappings', []):
                        if 'Ebs' in bd:
                            snapshot_id = bd['Ebs']['SnapshotId']
                            ec2.delete_snapshot(SnapshotId=snapshot_id)
                            logger.info(f"Deleted snapshot {snapshot_id} for AMI {image_id}")

                    deleted.append(image_id)
                except Exception as e:
                    logger.error(f"Failed to delete AMI {image_id}: {str(e)}")

        logger.info(f"Cleanup complete. Deleted {len(deleted)} expired AMIs.")
        return deleted
    except Exception as e:
        logger.error(f"Error during expired AMI cleanup: {str(e)}")
        return []


def lambda_handler(event, context):
    logger.info("Lambda execution started.")
    results = []
    success_count = 0
    failure_count = 0

    instance_ids = get_instance_ids()

    for instance_id in instance_ids:
        result = create_ami(instance_id)
        results.append(result)

        if result["status"] == "success":
            success_count += 1
        else:
            failure_count += 1

    deleted_amis = delete_expired_amis()

    message = f"""
EC2 Backup Report
Total Instances: {len(instance_ids)}
Success: {success_count}
Failed: {failure_count}
Deleted AMIs: {deleted_amis}
"""
    logger.info(f"Final Summary: {message}")

    try:
        if SNS_TOPIC:
            sns.publish(
                TopicArn=SNS_TOPIC,
                Message=message,
                Subject="EC2 Backup Status"
            )
            logger.info("SNS Notification sent.")
    except Exception as e:
        logger.error(f"SNS publish failed: {str(e)}")

    return {
        "statusCode": 200,
        "body": message
    }
