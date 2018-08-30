# Ovirt Engine and host details
# ovirt server ip
OVIRT_ENGINE_IP = '192.168.103.65'

# ovirt user name
OVIRT_ENGINE_UNAME = 'admin@internal'

# ovirt password
OVIRT_ENGINE_PASS = 'master@123'

# ovirt cluster name
CLUSTER_NAME='Default'

# vm template name in ovirt
TEMPLATE_NAME='automation_template_for_qcsbench_tool'

# template data domain
TEMPLATE_DS='DATA_DOMAIN'

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
SLAVE_PASSWORD='master@123'

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
# based on load type fio configuration file will be selected :-
# for block_io give the value of FIO_CONF_FILE = "test_fio.fio"
# for file_io give the value of FIO_CONF_FILE = "param_file_io.fio"
LOAD_TYPE = 'file_io'
# fio config file
FIO_CONF_FILE = "param_file_io.fio"

# log level
LOG_LEVEL = "DEBUG"

# log directory name
LOG_DIR = "output"

# fio result file
FIO_RESULT_FILE = "result.txt"


