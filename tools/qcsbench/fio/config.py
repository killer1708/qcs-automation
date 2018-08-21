# Ovirt Engine and host details
# ovirt server ip
OVIRT_ENGINE_IP = '192.168.105.161'

# ovirt user name
OVIRT_ENGINE_UNAME = 'admin@internal'

# ovirt password
OVIRT_ENGINE_PASS = 'admin'

# ovirt cluster name
CLUSTER_NAME='Default'

# vm template name in ovirt
TEMPLATE_NAME='automation_template_for_qcsbench_tool'

# template data domain
TEMPLATE_DS='ovirt_data'

# name of the vm to be created
VM_NAME='qcs_fio_vm'

# slave vm details
# number vm to be create
SLAVE_VM_COUNT=1
# slave vm type: linux|windows
HOST_TYPE = 'linux'
# vm user name
SLAVE_UNAME='root'
# vm password
SLAVE_PASSWORD='master#123'

# disk details
DISK_COUNT = 1
DISK_SIZE_GB = 50

# Current system details
# system user name
USERNAME = 'root'
# system password
PASSWORD = 'master#123'

# specify load details
# LOAD_TYPE possible values are - block_io and file_io
LOAD_TYPE = 'block_io'
# block io details

# verify data integrity - True|False
DATA_VALIDATION = False

# log level
LOG_LEVEL = "DEBUG"

# log directory name
LOG_DIR = "output"

