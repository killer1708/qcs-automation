# Ovirt Engine and host details
# ovirt server ip
OVIRT_ENGINE_IP = '192.168.105.61'

# ovirt user name
OVIRT_ENGINE_UNAME = 'admin@internal'

# ovirt password
OVIRT_ENGINE_PASS = 'admin'

# ovirt cluster name
CLUSTER_NAME='Default'

# vm template name in ovirt
TEMPLATE_NAME='champ'

# template data domain
TEMPLATE_DS='qcinder'

# name of the vm to be created
VM_NAME='qcs_fio_vm'

# slave vm details
# number vm to be create
SLAVE_VM_COUNT= 1
# slave vm type: linux|windows
HOST_TYPE = 'windows'
# vm user name
SLAVE_UNAME='admin'
# vm password
SLAVE_PASSWORD='admin'

# disk details
# Number of disks you want to add to individual vm.
DISK_COUNT = 1
# The size of disk/s you want to give for individual or mutliple vm/s.
DISK_SIZE_GB = 50

# Current system details
# system user name
USERNAME = 'msys'
# system password
PASSWORD = 'master#123'


# specify load details for linux
# LOAD_TYPE possible values are - block_io and file_io
# based on load type fio configuration file will be selected :-
# for block_io give the value of FIO_CONF_FILE = "test_fio.fio"
# for file_io give the value of FIO_CONF_FILE = "param_file_io.fio"
"""
LOAD_TYPE = 'block_io'
# fio config file
FIO_CONF_FILE = "test_fio.fio"
"""

# specify load details for windows
# LOAD_TYPE possible values are - block_io and file_io
# based on load type fio configuration file will be selected :-
# for block_io give the value of FIO_CONF_FILE = "test_fio_wind.fio"
# for file_io give the value of FIO_CONF_FILE = "param_file_io_wind.fio"

LOAD_TYPE = 'file_io'
# fio conf file
FIO_CONF_FILE = "param_file_io_wind.fio"

# log level
LOG_LEVEL = "DEBUG"

# log directory name
LOG_DIR = "output"

# fio result file
FIO_RESULT_FILE = "result.txt"

# Storage_Type either it can be IMAGE or CINDER
STORAGE_TYPE = "CINDER"

TOOL_NAME = "FIO"

