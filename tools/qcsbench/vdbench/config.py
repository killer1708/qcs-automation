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
VM_NAME='qcs_vdbench_vm'

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
# LOAD_TYPE possible values are - block_io|file_io.
# At a given instant, there could be only one LOAD_TYPE and
# corresponding WORKLOAD_INFO.
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
LOAD_TYPE = 'file_io'
WORKLOAD_INFO =  {
                  "fsd_params": {"depth": "1",
                                 "width": "1",
                                 "files": "3",
                                 "size": "1g"},
                  "fwd_params": {"operation": "write",
                                 "fileio": "sequential",
                                 "fileselect": "sequential",
                                 "threads": "1",
                                 "xfersize": "32k"},
                  "rd_params":  {"elapsed": "10",
                                 "fwdrate": "max",
                                 "maxdata": "1g",
                                 "format": "yes"}
                 }

# verify data integrity - True|False
DATA_VALIDATION = False

# log level
LOG_LEVEL = "DEBUG"

# log directory name
LOG_DIR = "output"
