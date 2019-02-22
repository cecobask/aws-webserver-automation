#!/usr/bin/env python3
import os
import subprocess
import sys
import time

import boto3
from botocore.exceptions import ClientError

ec2_client = boto3.client("ec2")
ec2 = boto3.resource("ec2")
s3 = boto3.resource("s3")


def create_instance(user_key, security_group, instance_name):
    instance = ec2.create_instances(
        ImageId="ami-08935252a36e25f85",
        InstanceType="t2.micro",
        KeyName=user_key[0],
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
                    sudo yum -y update
                    sudo yum -y install httpd
                    sudo yum -y install python36
                    sudo chkconfig httpd on
                    sudo /etc/init.d/httpd start'''
    )

    print(f"\nAn instance with ID {instance[0].id} is being created.")
    print("\nPlease wait while the public IP address of your instance is being fetched...")

    # A loop that will go on until it gets the public IP address of the instance
    while not instance[0].public_ip_address:
        try:
            instance[0].reload()
            if instance[0].public_ip_address:
                # Public IP address is available
                public_ip = instance[0].public_ip_address
                print(f"\nPublic IP address of instance {instance_name} ({instance[0].id}): {public_ip}")

                # Test ssh by running 'sudo ls -a' on the instance
                ssh_test(user_key[1], public_ip)

                # Copy check_webserver.py onto the instance
                copy_file_to_instance(user_key[1], public_ip)
        except Exception as e:
            print("\n", e, "\n")


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

    # If file extension is not .pem or file doesn't exist prompt the user for valid key
    while not key_path[-4:] == ".pem" or not os.path.isfile(os.path.expanduser(key_path)):
        key_path = input(f"\nEnter valid path to a .pem file, please.\n")

    key_name = key_path.split('/')[-1][:-4]
    print(f"\nSuccess. Path: {os.path.expanduser(key_path)} links to key: {key_name}.")

    # Make key read-only
    subprocess.Popen(f"chmod 400 {key_path}", shell=True)
    return key_name, key_path


# Get security group by name or id
def get_security_group():
    group_name = input("\nEnter security group name, please.\n")
    if group_name.startswith('sg-') and len(group_name) == 20:
        try:
            response = ec2_client.describe_security_groups(GroupIds=[group_name])
            print(
                f"\nSecurity group found by ID. Selected security group: {response['SecurityGroups'][0]['GroupName']}.")
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
    try:
        sec_group = ec2.create_security_group(GroupName=group_name, Description=group_name)
        sec_group.authorize_ingress(IpProtocol="tcp", CidrIp="0.0.0.0/0", FromPort=80, ToPort=80)
        sec_group.authorize_ingress(IpProtocol="tcp", CidrIp="0.0.0.0/0", FromPort=22, ToPort=22)
        print(f'\nCreated security group {group_name}(id:{sec_group.id}) with ports 80 & 22 open.')
        return sec_group.id
    except ClientError as e:
        print(e)


def ssh_test(key_path, pub_ip):
    # Status will always equal 255 on first run
    (status, output) = subprocess.getstatusoutput("ssh -t -o StrictHostKeyChecking=no -i " + key_path +
                                                  " ec2-user@" + pub_ip + " sudo ls -a")
    # Count the time elapsed for while loop
    timer = 0

    print("\nWaiting for instance to load.")

    # Loop through getting the status of running an SSH command until status 0
    while status == 255:
        timer += 1
        (status, output) = subprocess.getstatusoutput("ssh -t -o StrictHostKeyChecking=no -i " + key_path +
                                                      " ec2-user@" + pub_ip + " sudo ls -a")

        # SSH command was successful
        if status == 0:
            print("\nThe instance is ready to SSH.")
            break
        elif timer == 30:
            print(f"\nSSH test is taking too long to complete.{output}")
            break


def copy_file_to_instance(key_path, pub_ip):
    (status, output) = subprocess.getstatusoutput(
        "scp -i " + key_path + " check_webserver.py ec2-user@" + pub_ip + ":.")
    print("\nAttempting to copy check_webserver.py onto the instance.")
    if status == 0:
        print("\nCopied check_webserver.py onto the instance.")

        # Make script executable
        (status, output) = subprocess.getstatusoutput("ssh -t -o StrictHostKeyChecking=no -i " + key_path +
                                                      " ec2-user@" + pub_ip + " chmod 700 ./check_webserver.py")
        print("\nAttempting to run check_webserver.py on the instance. Please wait, it might take up to a minute...")

        if status == 0:
            (status, output) = subprocess.getstatusoutput("ssh -t -o StrictHostKeyChecking=no -i " + key_path +
                                                          " ec2-user@" + pub_ip + " ./check_webserver.py")
            countdown = 6

            # Loop until the script is finished being copied onto the instance
            while not status == 0:
                (status, output) = subprocess.getstatusoutput("ssh -t -o StrictHostKeyChecking=no -i " + key_path +
                                                              " ec2-user@" + pub_ip + " ./check_webserver.py")
                time.sleep(10)
                countdown -= 1

                # Command was successful
                if status == 0:
                    print(f"\nSuccessfully ran check_webserver.py on the instance.\nOutput: {output}\n")
                    break
                elif countdown == 0:
                    print(f"\nTook to long to run check_webserver.py on the instance.\n{output}\n")
                    break
        else:
            print(f"\nFailed to change permissions.\n{output}")
    else:
        print(f"\nCopying check_webserver.py failed.\n{output}")


def main():
    while True:
        menu()
        menu_choice = input("\n        Make a choice, please.     ")

        if menu_choice == "1":
            key = import_key_pair()
            security_group = get_security_group()
            instance_name = input("\nEnter name for your instance, please.\n")
            create_instance(key, security_group, instance_name)

        elif menu_choice == "0":
            print("\nClosing...")
            sys.exit(0)
        else:
            print("\n        Please, enter a valid choice.")


if __name__ == '__main__':
    main()
