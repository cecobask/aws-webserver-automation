#!/usr/bin/env python36
import subprocess


def run_apache():
    (status, output) = subprocess.getstatusoutput('sudo service httpd start')
    print(output)
    if status == 0:
        print("Apache Web Server is running.")
    else:
        install_apache()
        pass


# Check if Apache is running
def check_apache():
    (status, output) = subprocess.getstatusoutput("ps -A | grep httpd")
    if status == 0:
        print("Apache Web Server is running.")
    else:
        print(f"Apache Web Server is not running.{output}")
        run_apache()


def install_apache():
    choice = input("Would you like to install Apache Web Server?    ").lower()
    if choice in ['y', 'yes']:
        (status, output) = subprocess.getstatusoutput("sudo yum install httpd")
        if status == 0:
            print("Apache Web Server installed.")
            run_apache()
        else:
            print("An error occurred during installation.")
            print(output)
    else:
        print("Closing...")


def main():
    check_apache()


if __name__ == '__main__':
    main()
