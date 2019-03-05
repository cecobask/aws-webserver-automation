# aws-webserver-automation

A python script to automate the creation and management of EC2 instances, S3 buckets and uploading files to them.  
When an instance is created, 'check_webserver' script is copied onto that instance, which is later used to check the status of Apache Web Server.  
Querying of httpd access logs is possible and it provides information about all GET requests to the selected instance.

## Prerequisites

* Install **boto3** and **awscli**
* Run the following command to configure your boto3 credentials:
```console
  aws configure
```
* Generate a key-pair with this command and place it in .aws folder:
```console
  aws ec2 create-key-pair --key-name MyKeyPair --query 'KeyMaterial' --output text > ~/.aws/MyKeyPair.pem
```

## Getting Started

* Clone repository:
    
```console
  git@github.com:cecobask/aws-webserver-automation.git
```

* Make run_newwebserver.py executable:

```console
  chmod +x run_newwebserver.py
```

* Run script:
```console
  ./run_newwebserver.py
```

* Enter the path to your .pem file that you generated earlier.  
Key-pair should be located in ~/.aws/  

** **WARNING: Without a valid .pem file you will not be able to access the Menu.** **

![Menu](https://images2.imgbox.com/2f/04/h71dcXk2_o.jpg)

## Built With

* [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) - AWS SDK for Python
* [apache-log-parser](https://github.com/rory/apache-log-parser) - Parses httpd logs
* [subprocess](https://docs.python.org/3/library/subprocess.html) - Spawn new processes, connect to their input/output/error pipes, and obtain return codes
* [unittest](https://docs.python.org/3/library/unittest.html) - Python's built-in Unit Testing framework
* [importlib](https://docs.python.org/3/library/importlib.html) - Import modules dynamically

## Running the tests

* Open a Linux Terminal
* Make sure you have Python3 installed
* Run the following command in the terminal:
```console
  python3 TestFunctions.py 
```

## Versioning

[Git](https://git-scm.com/) was used for versioning.



## Authors

 **Tsvetoslav Dimov**  
 [LinkedIn](https://www.linkedin.com/in/cecobask/)