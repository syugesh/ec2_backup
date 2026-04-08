# **Automated EC2 Backup & retention system using AWS Lambda**

##  Overview

This project automates the backup of EC2 instances by creating Amazon Machine Images (AMIs) and managing their lifecycle using AWS services.

The system:

* Identifies EC2 instances tagged for backup
* Creates AMIs and snapshots automatically
* Applies retention policies for cleanup
* Logs execution details
* Sends notifications on completion

---

##  Architecture

###  Services Used

* AWS Lambda – Core backup and cleanup logic
* Amazon EventBridge – Scheduled trigger (cron job)
* Amazon EC2 – Instances, AMIs, and snapshots
* Amazon CloudWatch – Logging 
* Amazon SNS – Notifications (email alerts)

---

## 🔄 Workflow

1. EventBridge triggers Lambda on a schedule (e.g., daily)
2. Lambda fetches EC2 instances with tag:

   ```
   Backup=True
   ```
3. For each instance:

   * Create AMI
   * Automatically create snapshots
   * Tag AMI with retention metadata
4. Identify expired AMIs using:

   ```
   DeleteAfter tag
   ```
5. Cleanup process:

   * Deregister AMI
   * Delete associated snapshots
6. Log all actions in CloudWatch
7. Send summary notification via SNS

---

##  Project Structure

```
project/
│── lambda_function.py
│── README.md
```

---

## Prerequisites

* AWS Account
* IAM Role with permissions:

  * EC2 (Describe, CreateImage, DeleteSnapshot, DeregisterImage)
  * CloudWatch Logs
  * SNS Publish
* Python 3.x
* AWS CLI configured (optional for deployment)

---

## 🔑 Environment Variables

Set the following variables in Lambda:

| Variable Name  | Description                     | Example                          |
| -------------- | ------------------------------- | -------------------------------- |
| sns_topic      | SNS Topic ARN for notifications | arn:aws:sns:region:acct-id:topic |
| retention_days | Backup retention period         | 7                                |

---

## 🏷️ Tagging Requirement

Ensure EC2 instances have the following tag:

```
Key: Backup
Value: True
```

Only tagged instances will be backed up.

---

## Deployment Steps

### 1. Create IAM Role

* Attach policies:

  * AmazonEC2FullAccess (or limited custom policy)
  * CloudWatchLogsFullAccess
  * AmazonSNSFullAccess

---

### 2. Create Lambda Function

* Runtime: Python 3.x
* Upload your `lambda_function.py`
* Attach IAM role
* Add environment variables

---

### 3. Configure EventBridge Trigger

* Create rule with cron expression:

  ```
  cron(0 2 * * ? *)
  ```
* Target: Lambda function

---

### 4. Setup SNS Notifications

* Create SNS Topic
* Subscribe your email
* Confirm subscription
* Add topic ARN to Lambda environment variable

---

##  How to Run

### Manual Execution

1. Go to AWS Lambda Console
2. Select your function
3. Click **Test**
4. View logs in CloudWatch

---

### Automatic Execution

* Runs automatically based on EventBridge schedule

---

## 📊 Logging 

* Logs are stored in CloudWatch:

  ```
  /aws/lambda/<function-name>
  ```
* Logs include:

  * Execution start/end
  * AMI creation status
  * Errors
  * Cleanup actions

---

## 📢 Notification Example

```
EC2 Backup Report
Total Instances: 3
Success: 3
Failed: 0
Deleted AMIs: ['ami-12345']
```

---

##  Key Features

* Automated AMI & snapshot creation
* Tag-based instance selection
* Retention-based cleanup
* Error handling & logging
* SNS notification system

---
