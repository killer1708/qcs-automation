# Ovirt Engine and host details

# ovirt server ip
OVIRT_ENGINE_IP = '192.168.105.161'

# ovirt server name
OVIRT_ENGINE_UNAME = 'admin@internal'

# ovirt server password
OVIRT_ENGINE_PASS = 'admin'

# ovirt cluster nMW
CLUSTER_NAME='Default'

# automation template name
TEMPLATE_NAME='automation_template_for_qcsbench_tool'

# ovirt storage name
TEMPLATE_DS='ovirt_data'

# vm name for creating vm on ovirt
VM_NAME='qcs_iometer_vm'

# slave vm details
# number of vm to create
SLAVE_VM_COUNT=1
# vm user name
SLAVE_UNAME='root'
# vm password
SLAVE_PASSWORD='master#123'
# slave vm host type, possible values - linux|windows
HOST_TYPE = 'linux'
# load type on slave vms, possible values - block_io|file_io
# TODO:
LOAD_TYPE = 'block_io'

# ADD Disk details
# number of disk to add
DISK_COUNT=1
# disk name
DISK_NAME='user_disk'
# disk size
DISK_SIZE_GB = 50

# Current machine details
# user name
CURRENT_UNAME='root'
# password
CURRENT_PASSWD='master#123'

# dynamo path from copy
LOCAL_PATH = 'dynamo'
# dynamo path to copy on remote machine
REMOTE_PATH = '/root/dynamo'

# Iometer server credential
# Iometer server ip
IOMETER_SERVER = '192.168.102.85'
# user name
IOMETER_UNAME = 'admin'
# password
IOMETER_PASSWD = 'admin'

# Iometer exe location
IOMETER_SDK = "C:\\Users\\Administrator\\Desktop\\iometer_sdk\\"
# Iometer config file path
IOMETER_CONFIG_FILE = "test_iometer.icf"
# IOMETER output dir
IOMETER_OUTPUT_DIR = "output"
# IOMeter result file name
IOMETER_RESULT_FILE_NAME = "result.csv"

# output log direcctory
LOG_DIR = "output"
LOG_LEVEL = "DEBUG"
