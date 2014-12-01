import ConfigParser
from pysnmp.entity.rfc3413.oneliner import cmdgen
import time
import os
import sys
import multiprocessing


#class that holds each config file. Every config file defines class of machines to be listened
class machineClass:
    def __init__(self,filename):
        self.Config=ConfigParser.ConfigParser()
        self.Config.read(filename)
        self.timeout=float(self.Config.get('general','timeout'))
        ip_uuid=self.ip_lookup(self.Config)
        self.hosts=list()
        for uuid in ip_uuid:
            self.hosts.append(self.snmpHost(uuid,ip_uuid[uuid],self.Config))

#function that generates machine uuid and ip pair for each hosts in the machineClass instance
    def ip_lookup(self,Config):
        ip_uuid={}
        for uuid in Config.options('hosts'):
            ip_uuid[uuid]=Config.get('hosts',uuid)
        return ip_uuid

#each machine in machineClass is a different instance of class snmpHost
    class snmpHost:
        def __init__(self,uuid,ip,Config):
            self.Config=Config
            self.ip=ip
            self.uuid=uuid
#first two sections of .ini files are general information about the machine class and list of hosts included. Every section onwards is snmp oids to listen.
            self.sections=self.Config.sections()[2:]
#every line in sections of .ini files consists of human readable option and numeric OIDs. Storing all options with respect to their section
            self.options={}
            for section in self.sections:
                self.options[section]=self.Config.options(section)

#function to retrieve numeric OID
        def get_oid(self,section):
            oids_numeric=list()
            i=0
            while i<len(self.options[section]):
                oids_numeric.append(self.Config.get(section,self.options[section][i]))
                i=i+1
            return oids_numeric

#function to send SNMP Get request to host and return the response.
        def snmpGet(self,oid):
                cmdGen = cmdgen.CommandGenerator()
                errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
                    cmdgen.CommunityData('public'),
                    cmdgen.UdpTransportTarget((self.ip, 161)),
                    *oid
                    )
# Check for errors and return result as a list. If any error in SNMP halt the program.
                if errorIndication:
                     sys.exit(errorIndication)
                else:
                    if errorStatus:
                        a='%s at %s' % (
                            errorStatus.prettyPrint(),
                            errorIndex and varBinds[int(errorIndex) - 1] or '?'
                        )
                        sys.exit(a)
                    else:
                        return varBinds

#function to generate timestamp in milliseconds interval and return it as string
        def timestamp(self):
                now = time.time()
                localtime = time.localtime(now)
                milliseconds = '%03d' % int((now - int(now)) * 1000)
                return time.strftime('%Y%m%d%H%M%S', localtime) + milliseconds

#function to generate storage path. Storage path would be form of: ../stor/year/month/day/
        def storage_path_check(self,currentTime):
            storage_path=os.getcwd()+'/'+'stor'+'/'+currentTime[:4]+'/'+currentTime[4:6]+'/'+currentTime[6:8]
            try:
                 os.makedirs(storage_path)
            except OSError, e:
                return storage_path
            return storage_path

#function to generate filename. Filename would be in form of: YearMMDay:uuid:SNMP:section.txt[collector name]
        def fileName(self,section):
            path=self.storage_path_check(self.timestamp())
            filename=self.timestamp()[:8]+':'+self.uuid+':'+'SNMP'+':'+section+'.txt'+'['+self.Config.get('general','collector name')+']'
            return path+'/'+filename

#function to write SNMP Get response into file. First it will write every option in the section of .ini file, second timestamp of it, third the value as response pair
        def dataWrite(self,section,snmp_response):
            f=open(self.fileName(section),'a+')
            i=0
            for response_pair in snmp_response:
                f.write('\n' + self.options[section][i] + ', ' + self.timestamp() + ', ' + str(response_pair[1]))
                i=i+1
            f.close()

#function that actually triggers the functions to generate SNMP get response and write to disk
        def snmpListen(self):
            for section in self.sections:
                self.dataWrite(section,self.snmpGet(self.get_oid(section)))

#Global function to generate the names of config files.
def getConfigFile():
    directory=os.getcwd()+'/config'
    files=os.listdir(directory)
    configFileNames=list()
#Check if ../config folder exists and if yes fetch all the files that ends with .ini
    try:
        for filename in files:
            a=directory+'/'+filename
            if os.path.isfile(a) and a.endswith('.ini'):
                configFileNames.append(a)
    except OSError:
        print 'config directory not found'
    return configFileNames

#Global function to run snmpListen for every hosts of every machine class
def mp_handler(machine_class):
    i=0
    while i<len(machine_class):
        y=0
        while y<len(machine_class[i].hosts):
            machine_class[i].hosts[y].snmpListen()
            time.sleep(machine_class[i].timeout)
            y=y+1
        i=i+1

#main function
def main():
#fetch the names of all machine class from the list of config files.
    ConfigFiles=getConfigFile()
    machine_class=list()
#for every machine class create instance of machineClass class
    for filename in ConfigFiles:
        machine_class.append(machineClass(filename))
#continuously and sequentially run snmpListen function for each host of each machine class.
    while 1:
        mp_handler(machine_class)

if __name__=='__main__':
    main()
