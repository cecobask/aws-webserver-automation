#!/usr/bin/env python3
import boto3
import sys
import os
from botocore.exceptions import ClientError
from pathlib import Path

ec2_client = boto3.client("ec2")
ec2 = boto3.resource("ec2")
s3 = boto3.resource("s3")


# Get security group by name or id
def get_security_group():
    group_name = input("\nEnter security group name, please.\n")
    if group_name.startswith('sg-') and len(group_name) == 20:
        try:
            response = ec2_client.describe_security_groups(GroupIds=[group_name])
            print(f"\nSecurity group found by ID. Selected security group: {response['SecurityGroups'][0]['GroupName']}.")
            return response['SecurityGroups'][0]['GroupId']
        except ClientError as e:
            print("\n", e)
            return create_security_group(group_name)
    else:
        try:
            response = ec2_client.describe_security_groups(GroupNames=[group_name])
            print(f"\nSecurity group found by name. Selected security group: {group_name}.")
            return response['SecurityGroups'][0]['GroupId']
        except ClientError as e:
            print("\n", e)
            return create_security_group(group_name)


def create_security_group(group_name):
    sec_group = ec2.create_security_group(GroupName=group_name, Description=group_name)
    sec_group.authorize_ingress(IpProtocol="tcp", CidrIp="0.0.0.0/0", FromPort=80, ToPort=80)
    sec_group.authorize_ingress(IpProtocol="tcp", CidrIp="0.0.0.0/0", FromPort=22, ToPort=22)
    print(f'\nCreated security group {group_name}(id:{sec_group.id}) with ports 80 & 22 open.')
    return sec_group.id


def create_instance(user_key, security_group, instance_name):
    instance = ec2.create_instances(
        ImageId="ami-0fad7378adf284ce0",
        InstanceType="t2.micro",
        KeyName=user_key,
        MinCount=1,
        MaxCount=1,
        # Security group is pre-configured to allow public access
        SecurityGroupIds=[security_group],
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': instance_name
                    },
                ]
            },
        ],
        UserData='''#!/bin/bash
                    yum -y update
                    yum -y install nginx
                    yum -y install python3
                    service nginx start
                    chkconfig nginx on'''
    )

    print(f"\nAn instance with ID {instance[0].id} has been created.\n")


def menu():
    print('''
        + — — — — — — — — — — — — — — — — — — — — — — — — — + 
        |   Welcome to AWS Web server Automation script!    |
        |                                                   |
        |   1. Create an instance                           |
        |   2. Create a bucket                              |
        |   3. Upload file to a bucket                      |
        |                                                   |
        |   0. Exit                                         |
        + — — — — — — — — — — — — — — — — — — — — — — — — — +''')


def import_key_pair():
    key_path = input("\nEnter the path to your key pair. (including the .pem extension)\n")
    
    while not key_path[-4:] == ".pem" or not os.path.isfile(os.path.expanduser(key_path)):
        key_path = input(f"\nEnter valid path to a .pem file, please.\n")

    key_name = key_path.split('/')[-1][:-4]
    print(f"\nSuccess. Path: {os.path.expanduser(key_path)} links to key: {key_name}.")
    return key_name




def main():

    while True:
        menu()
        menu_choice = int(input("\n        Make a choice, please.     "))

        if menu_choice==1:
            key = import_key_pair()
            security_group = get_security_group()
            instance_name = input("\nEnter name for your instance, please.\n")
            create_instance(key,security_group,instance_name)

        elif menu_choice==0:
            print("\nClosing...")
            sys.exit(0)
        else:
            print("\n        Please, enter a valid choice.")


if __name__ == '__main__':
    main()
