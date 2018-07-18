# Ovirt Engine and host details

#ovirt server ip
OVIRT_ENGINE_IP = '192.168.103.65'

#ovirt server name
OVIRT_ENGINE_UNAME = 'admin@internal'

#ovirt server password
OVIRT_ENGINE_PASS = 'master@123'

#ovirt cluster nMW
CLUSTER_NAME='QCSCL'

#automation template name
TEMPLATE_NAME='automation_template2'

# ovirt storage name
TEMPLATE_DS='DATA_DOMAIN'

#vm name for creating vm on ovirt
VM_NAME='qcs_vm_io'

#slave vm details
#number of vm to create
SLAVE_VM_COUNT=1

#vm user name
SLAVE_UNAME='root'

#vm password
SLAVE_PASSWORD='master@123'

#ADD Disk
#number of disk to add
DISK_COUNT=1
#disk name
DISK_NAME='disk_name'

# Master vm details
#master vm user name
MASTER_UNAME='root'
#master vm password
MASTER_PASSWD='master@123'

#dynamo path from copy
LOCAL_PATH = 'test_fio.fio'
#dynamo path to copy on remote machine
REMOTE_PATH = '/root/dynamo'

#iometer server credential
#iometer server ip
IOMETER_SERVER = '192.168.102.85'
#iometer server user name
IOMETER_UNAME = 'administrator'
#iometer server password
IOMETER_PASSWD = 'master@123'

#iometer exe location
IOMETER_SDK = "C:\\Users\\Administrator\\Desktop\\iometer_sdk\\"
#iometer config file path
IOMETER_CONFIG_FILE = "/root/automation/new/qcs-automation/tools/qcsbench/iometer/test_iometer.icf"
#IOMETER output dir
IOMETER_OUTPUT_DIR = "/root/automation/new/qcs-automation/tools/qcsbench/iometer/output/"
#IOMeter result file name
IOMETER_RESULT_FILE_NAME = "result.csv"

