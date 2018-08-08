# Ovirt Engine and host details
# ovirt server ip
OVIRT_ENGINE_IP = '192.168.103.65'

# ovirt user name
OVIRT_ENGINE_UNAME = 'admin@internal'

# ovirt password
OVIRT_ENGINE_PASS = 'master@123'

# ovirt cluster name
CLUSTER_NAME='QCSCL'

# vm template name in ovirt
# TEMPLATE_NAME='automation_template2'
TEMPLATE_NAME='test_template_with_ip'

# template data domain
TEMPLATE_DS='DATA_DOMAIN'

# name of the vm to be created
VM_NAME='qcs_vm'

# slave vm details
# number vm to be create
SLAVE_VM_COUNT=2
# slave vm type
HOST_TYPE = 'linux'
# vm user name
SLAVE_UNAME='root'
# vm password
SLAVE_PASSWORD='master@123'

# Current system details
# system user name
USERNAME = 'root'
# system password 
PASSWORD = 'master#123'

# vdbench configuration file
SAMPLE_VDB_CONFIG='../../../libs/qcsbench'

# specify load details
# LOAD_TYPE possible values are - block_io and file_io
LOAD_TYPE = 'block_io'
# block io details
WORKLOAD_INFO =  {
                  "sd_params": {"threads":"1",
                                "openflags":"o_direct"},
                  "wd_params": {"rdpct":"0",
                                "seekpct":"0",
                                "xfersize":"4k"},
                  "rd_params": {"elapsed":"10",
                                "iorate" : "max"}
                 }
# file io details

# log level
LOG_LEVEL = "DEBUG"

# disk details
DISK_COUNT = 1
DISK_SIZE_GB = 50
