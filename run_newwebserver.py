#!/usr/bin/env python3
import os
import subprocess
import sys
import time
import apache_log_parser
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
        + — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — —  — — — — — + 
        |   Welcome to AWS Web server Automation script!                                 |
        |                                                                                |
        |   1.  Create an instance                                                       |
        |   2.  Create bucket (Optional: upload image + append to Apache's index.html)   |
        |   3.  Upload file to a bucket                                                  |
        |   4.  List buckets                                                             | 
        |   5.  List running instances                                                   |
        |   6.  List security groups                                                     |
        |   7.  Delete bucket                                                            |
        |   8.  Terminate instances                                                      |
        |   9.  Web server status                                                        |
        |   10. Query server access_log (display GET Requests)                           |
        |                                                                                |
        |   0. Exit                                                                      |
        + — — — — — — — — — — — — — — — — — — — — — — — — — — —— — — — — — — — — — — — — +''')


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


def list_security_groups():
    # Empty dictionary to store security group IDs
    sec_groups_dict = {}
    response = ec2_client.describe_security_groups()
    # Start the for loop from 1
    i = 1
    # Print header
    print('\n#', '\tSecurityGroup ID', '\t\tSecurityGroup Name')
    # Iterate through all security groups
    for group in response['SecurityGroups']:
        # Map i as key to security group ID value
        sec_groups_dict[str(i)] = group['GroupId']
        if len(group['GroupId']) > 11:
            print(i, '\t' + group['GroupId'], '\t\t' + group['GroupName'])
        else:
            print(i, '\t' + group['GroupId'], '\t\t\t' + group['GroupName'])
        i += 1

    # No security groups found
    if len(sec_groups_dict) == 0:
        print("\nNo security groups found.")
    else:
        return sec_groups_dict


def select_security_group(sec_groups_dict):
    while True:
        choice = input("\nEnter security group number or enter 'new' to create a security group: ")
        # Return the chosen security group ID
        try:
            if int(choice) not in range(len(sec_groups_dict) + 1):
                print(f"\nOption not in range. Pick a valid number.")
            else:
                print(f"\nYou selected security group with ID: {sec_groups_dict[choice]}")
                return sec_groups_dict[choice]
        except Exception:
            if choice.lower() == "new":
                sec_group_name = input("\nEnter name for your security group, please.   ")
                create_security_group(sec_group_name)
                break
            else:
                print("\nYou have to enter an integer!")


def create_security_group(group_name):
    try:
        sec_group = ec2.create_security_group(GroupName=group_name, Description=group_name)
        sec_group.authorize_ingress(IpProtocol="tcp", CidrIp="0.0.0.0/0", FromPort=80, ToPort=80)
        sec_group.authorize_ingress(IpProtocol="tcp", CidrIp="0.0.0.0/0", FromPort=22, ToPort=22)
        print(f'\nCreated security group {group_name} (id:{sec_group.id}) with ports 80 & 22 open.')
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
                    print(f"\nSuccessfully ran check_webserver.py on the instance.\n\nStatus: {output}\n")
                    break
                elif countdown == 0:
                    print(f"\nTook to long to run check_webserver.py on the instance.\n{output}\n")
                    break
        else:
            print(f"\nFailed to change permissions.\n{output}")
    else:
        print(f"\nCopying check_webserver.py failed.\n{output}")


def create_bucket(key_path):
    while True:
        bucket_name = input("Choose bucket name, please. (tip: lowercase, do not use underscores)\n").lower()
        try:
            response = s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'})
            print(f"\nCreated bucket with name {response.name}.")
            choice = input("\nWould you like to upload an image to this bucket? (y/n)   ").lower()
            if choice in ['yes', 'y']:
                upload_file(bucket_name, key_path)
                break
            elif choice in ['no', 'n']:
                break
            else:
                print("\nEnter 'y' or 'n', please.")
            break
        except Exception as error:
            print("\n", error, "\n")


def upload_file(bucket_name, key_path, file_path='./photo.jpeg', key_name='photo.jpeg'):
    try:
        s3.Bucket(bucket_name).upload_file(
            file_path,  # Path to file
            key_name,  # Key name
            ExtraArgs={'ACL': 'public-read'})  # Make it public readable
        print(f"\nUploaded '{key_name}' to bucket {bucket_name}.\n"
              f"URL: http://s3-eu-west-1.amazonaws.com/{bucket_name}/{key_name}")

        # Check if file is image
        while key_name.lower().endswith(('.jpg', '.jpeg', '.gif', '.bmp', '.png', 'svg')):
            choice = input("\nWould you like to add the file to Apache index page? (y/n):    ").lower()
            if choice in ['yes', 'y']:
                public_ip = select_instance(list_instances())
                if public_ip:
                    try:
                        create_index_page(public_ip,
                                          key_path,
                                          f"http://s3-eu-west-1.amazonaws.com/{bucket_name}/{key_name}")
                        break
                    except Exception as error:
                        print(error)
            elif choice in ['no', 'n']:
                break
            else:
                print("\nEnter 'y' or 'n', please.")

    except Exception as error:
        print("\n", error, "\n")


def list_instances():
    # Empty dictionary to store IPs for instances
    instance_ips = {}
    # Start the for loop from 1
    i = 1
    # Iterate through all instances
    for instance in ec2.instances.all():
        # Actions to take when first running instance found
        if instance.state['Name'] == 'running' and i == 1:
            # Print header
            print('\n#', '\tInstance ID', '\t\tIP Address')
            # Map i as key to instance IP address value
            instance_ips[str(i)] = instance.public_ip_address
            print(i, '\t' + instance.id, '\t' + instance.public_ip_address)
            i += 1
        elif instance.state['Name'] == 'running':
            # Map i as key to instance IP address value
            instance_ips[str(i)] = instance.public_ip_address
            print(i, '\t' + instance.id, '\t' + instance.public_ip_address)
            i += 1

    # No instances are running
    if len(instance_ips) == 0:
        print("\nNo running instances. You can create an instance by using option 1 of the main menu.")
    else:
        return instance_ips


def select_instance(instance_ips):
    while True:
        choice = input("\nEnter instance number: ")
        try:
            # Return the chosen instance IP address
            print(f"You selected instance with IP {instance_ips[choice]}")
            return instance_ips[choice]
        except Exception as error:
            print(f"\nNot a valid option. Pick a valid number.\n{error}")


def list_buckets():
    # Empty dictionary to store bucket names
    buckets_dict = {}
    # Start the for loop from 1
    i = 1
    print('\n#', '\tBucket name')
    # Iterate through all buckets
    for bucket in s3.buckets.all():
        # Map i as key to bucket name value
        buckets_dict[str(i)] = bucket.name
        print(i, '\t' + bucket.name)
        i += 1

    # No buckets found
    if len(buckets_dict) == 0:
        print("\nNo buckets found. You can create a bucket by using option 2 of the main menu.")
    # If there are s3 buckets, ask the user to choose an option
    else:
        return buckets_dict


def select_bucket(buckets_dict):
    while True:
        choice = input("\nEnter bucket number:  ")
        try:
            # Return the chosen bucket name
            print(f"\nYou selected bucket: {buckets_dict[choice]}")
            return buckets_dict[choice]
        except Exception as error:
            print(f"\n{error} is not a valid option.")


def delete_bucket():
    bucket = s3.Bucket(select_bucket(list_buckets()))
    for key in bucket.objects.all():
        key.delete()
    bucket.delete()
    print(f"\nSuccessfully deleted bucket: {bucket.name}\n")


def terminate_instances():
    terminated_count = 0
    for instance in ec2.instances.all():
        if not instance.state['Name'] == 'terminated':
            instance.terminate()
            print(f"\nTerminated instance: {instance.id}\n")
            terminated_count += 1

    if not terminated_count == 0:
        print(f"\nTerminated instances count: {terminated_count}.\n")
    else:
        print("\nNo instances to terminate.")


def create_index_page(public_ip, key_path, url):
    image_tag = f'<img src="{url}">'
    echo_index = f"sudo echo '{image_tag}' > index.html"
    permissions = f"ssh -t -o StrictHostKeyChecking=no -i {key_path} ec2-user@{public_ip} sudo chmod o+w /var/www/html"
    transfer_index = f'rsync --remove-source-files -az -e "ssh -i {key_path}" index.html ec2-user@{public_ip}:/var/www/html'

    # Append <img> tag to index.html
    (status, output) = subprocess.getstatusoutput(echo_index)
    if status == 0:
        print("\nAppended <img> tag with src = image url from your s3 bucket to index.html")
    else:
        print("\n", output, "\n")

    # Give write access to /var/www/html folder
    (status, output) = subprocess.getstatusoutput(permissions)

    # Wait until instance is loaded
    while not status == 0:
        (status, output) = subprocess.getstatusoutput(permissions)

    if status == 0:
        print("\nChanged the permissions for /var/www/html/")
    else:
        print("\n", output, "\n")

    # Transfer index.html
    (status, output) = subprocess.getstatusoutput(transfer_index)
    if status == 0:
        print(f"\nTransferred index.html to EC2 instance ({public_ip}).")
    else:
        print("\n", output, "\n")

    # Open Apache Web Server localhost in Firefox to view the image
    subprocess.call(['firefox', '-new-tab', public_ip])
    print(f"\nOpening Apache Web Server home page ({public_ip}) in Firefox.")


def check_web_server(pub_ip, key_path):
    # Run check_webserver.py
    (status, output) = subprocess.getstatusoutput("ssh -t -o StrictHostKeyChecking=no -i " + key_path +
                                                  " ec2-user@" + pub_ip + " ./check_webserver.py")

    # Command was successful
    if status == 0:
        print(f"\nSuccessfully ran check_webserver.py on the instance.\n\nStatus: {output}\n")
    else:
        print(output)


# https://github.com/rory/apache-log-parser
def query_logs(key_path):
    ip_address = select_instance(list_instances())
    # Specify logs format for parser
    line_parser = apache_log_parser.make_parser("%h %l %u %t \"%r\" %>s %b")
    # Use grep to filter out only the lines with GET Requests
    ssh = f"ssh -t -o StrictHostKeyChecking=no -i {key_path} ec2-user@{ip_address} -q sudo cat /var/log/httpd/access_log | grep GET"
    cmd = subprocess.Popen(ssh, shell=True, universal_newlines=True, stdout=subprocess.PIPE)
    print("\n\t*****  ALL GET REQUESTS FROM APACHE WEB SERVER ACCESS LOG  *****")
    print("\n\n\tIP Address\t\tTime Received\t\t\tStatus")
    # Read each line from output and parse it with apache_log_parser
    for line in cmd.stdout.readlines():
        log_line_data = line_parser(line)
        print(f"\t{log_line_data['remote_host']}\t\t{log_line_data['time_received_isoformat']}\t\t{log_line_data['status']}")


def main():
    # Ask the user for path to their key pair
    key_pair = import_key_pair()

    while True:
        menu()
        menu_choice = input("\n        Make a choice, please.     ")

        if menu_choice == "1":
            security_group = select_security_group(list_security_groups())
            instance_name = input("\nEnter name for your instance, please.\n")
            create_instance(key_pair, security_group, instance_name)
        elif menu_choice == "2":
            create_bucket(key_pair[1])
        elif menu_choice == "3":
            # Let the user choose which bucket to upload file to
            bucket_name = select_bucket(list_buckets())
            file_path = os.path.expanduser(input("\nPlease enter the path to the file you want to upload:\n"))
            # If file doesn't exist prompt the user for valid file
            while not os.path.isfile(file_path):
                print(f"\nPath: {file_path} does not link to a valid file.")
                file_path = os.path.expanduser(input("\nPlease enter a valid path to the file you want to upload:\n"))
            # Extract only the file name from the path and use it as a key
            key_name = str(file_path.split('/')[-1])
            upload_file(bucket_name, key_pair[1], os.path.expanduser(file_path), key_name)
        elif menu_choice == "4":
            list_buckets()
        elif menu_choice == "5":
            list_instances()
        elif menu_choice == "6":
            list_security_groups()
        elif menu_choice == "7":
            delete_bucket()
        elif menu_choice == "8":
            terminate_instances()
        elif menu_choice == "9":
            ip_address = select_instance(list_instances())
            check_web_server(ip_address, key_pair[1])
        elif menu_choice == "10":
            query_logs(key_pair[1])
        elif menu_choice == "0":
            print("\nClosing...")
            sys.exit(0)
        else:
            print("\n        Please, enter a valid choice.")


if __name__ == '__main__':
    main()
