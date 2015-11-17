#!/usr/bin/python

import gevent.monkey; gevent.monkey.patch_all()
from pssh import ParallelSSHClient
import paramiko,threading,re,sys,getopt,time

def usage():
	print "Test RBD on multiple host"
	print "Usage:"
	print "-h --help"
	print "-b --block_size default=4096 KB"
	print "-t --test_mode default=randwrite"
	print "-s --size default=4 MB"
	print "-p --pool default=cold-storage"
	print "-n --jobs_number default=4"
	print "-u --unit-test default=no"

def unit_test():
	print "Test passed"

def run_fio(block_size, test_mode, size_fio, pool_fio, num_jobs):
	client_key = paramiko.RSAKey.from_private_key_file('/root/.ssh/id_rsa')
	hosts = ['node06', 'node07', 'node08', 'node09', 'node10', 'node11']
	client = ParallelSSHClient(hosts, pkey=client_key)
	output = client.run_command("rbd create $HOSTNAME --size "+size_fio+" -k /etc/ceph/ceph.client.admin.keyring --pool "+pool_fio)
	for host in output:
		for line in output[host]['stdout']:
			print "Host %s - output: %s" % (host, line)
	output = client.run_command("fio --name=fio-test --ioengine=rbd  --pool="+pool_fio+" --rbdname=$HOSTNAME --iodepth=32 --rw="+test_mode+" --bs="+block_size+"k --direct=0 --size="+size_fio+"M --numjobs="+num_jobs)
	client.pool.join()
	aggregate={}
	for host in output:
        	for line in output[host]['stdout']:
			pattern = re.compile("^WRITE: io=|^READ: io=")
			if pattern.match(line):
				aggregate[host]=line
                		print "Host %s - output: %s" % (host, line)
	
	n=0
	for host in aggregate:
		str = aggregate[host]
		m = re.search("(?:aggrb=([0-9]+))",str).group(1)
		n = n+int(m)
	print "Total bandwidth aggregate=%sKB/s" % n
	time.sleep(10)
	output = client.run_command("rbd rm $HOSTNAME --pool "+pool_fio)
	client.pool.join()
        for host in output:
                if output[host]['exit_code'] != 0:
			print "Error removing rbd device"
			sys.exit(1)

def main(argv):
        block_size = '4096'
        test_mode = 'randwrite'
        size_fio = '50'
        pool_fio = 'cold-storage'
        num_jobs = '4'
        try:
                opts, args = getopt.getopt(argv,"hub:t:s:p:n",["help", "unit-test", "block_size=", "test_mode=", "size=", "pool", "jobs_number="])
        except getopt.GetoptError:
                usage()
                sys.exit(2)
        for opt, arg in opts:
                if opt in ("-h", "--help"):
                        usage()
                        sys.exit()
                elif opt in ("-b", "--block_size"):
                        block_size = arg
                elif opt in ("-t", "--test_mode"):
                        test_mode = arg
                elif opt in ("-s", "--size"):
                        size_fio = arg
                elif opt in ("-p", "--pool"):
                        pool_fio = arg
                elif opt in ("-n", "--jobs_number"):
                        num_jobs = arg
		elif opt in ("-u", "--unit-test"):
			unit_test()
			sys.exit()
			
        run_fio(block_size, test_mode, size_fio, pool_fio, num_jobs)

if __name__ == "__main__":
        main(sys.argv[1:])
