# Ovirt Engine and host details

# ovirt server ip
OVIRT_ENGINE_IP = '192.168.105.224'

# ovirt server name
OVIRT_ENGINE_UNAME = 'admin@internal'

# ovirt server password
OVIRT_ENGINE_PASS = 'admin'

# ovirt cluster nMW
CLUSTER_NAME = 'Default'

# automation template name
TEMPLATE_NAME = 'rock'

# ovirt storage name
TEMPLATE_DS = 'qcinder'

# vm name for creating vm on ovirt
VM_NAME = 'qcs_iometer_vm'

# slave vm details
# number of vm to create
SLAVE_VM_COUNT=4
# vm user name
#SLAVE_UNAME='root'
SLAVE_UNAME ='root'
# vm password
#SLAVE_PASSWORD='master@123'
SLAVE_PASSWORD ='master#123'
# slave vm host type, possible values - linux|windows
HOST_TYPE = 'linux'
#HOST_TYPE = 'windows'
# load type on slave vms, possible values - block_io|file_io
#LOAD_TYPE = 'file_io'
LOAD_TYPE = 'block_io'

# workload info
WORKLOAD_INFO = {
                 'no_of_worker' : '1',
                 'size_in_sector' : '81960',
                 'access_specification' : ['512 B; 50% Read; 0% random',
                                           '4 KiB; 75% Read; 0% random']
                }


# ADD Disk details
# number of disk to add with there interface detail respectively
INTERFACES = ['IDE']
# disk name
DISK_NAME='user_disk'
# disk size
DISK_SIZE_GB = 50

# Current machine details
# user name
CURRENT_UNAME='root'
# password
CURRENT_PASSWD='master#123'
#CURRENT_PASSWD='master#123'
# dynamo path from copy
LOCAL_PATH = 'dynamo'
# dynamo path to copy on remote machine
REMOTE_PATH = '/root/dynamo'
#REMOTE_PATH = 'C:\\dynamo'

# Iometer server credential
# Iometer server ip
#IOMETER_SERVER = '192.168.102.85'
IOMETER_SERVER = '192.168.102.185'
# user name
IOMETER_UNAME = 'admin'
# password
IOMETER_PASSWD = 'admin'

# Iometer exe location
#IOMETER_SDK = "C:\\Users\\msys\\Desktop\\iometer_sdk\\"
IOMETER_SDK = "C:\\iometer\\"
# Iometer config file path
IOMETER_CONFIG_FILE = "test_iometer.icf"
# IOMETER output dir
IOMETER_OUTPUT_DIR = "output"
# IOMeter result file name
IOMETER_RESULT_FILE_NAME = "result.csv"

WIN_IOMETER_EXC_LOC = "iometer"


# output log direcctory
LOG_DIR = "output"
LOG_LEVEL = "DEBUG"

#Base IOmeter file name
BASE_IOMETER_FILE = "iometer.icf"

#Storage_Type either it can be IMAGE or CINDER
#STORAGE_TYPE = "IMAGE"
STORAGE_TYPE = "CINDER"
