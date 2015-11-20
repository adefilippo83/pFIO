#!/usr/bin/python

import gevent.monkey; gevent.monkey.patch_all()
from pssh import ParallelSSHClient
import paramiko,threading,re,sys,getopt,time,unittest,ConfigParser,io

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


class FioTestCase(unittest.TestCase):
	def runTest(self):	
		block_size = '4096'
		test_mode = 'randwrite'
		size_fio = '50'
		pool_fio = 'cold-storage'
		num_jobs = '4'
		hosts = ['localhost']
		io_engine = 'rbd'
		io_depth = '32'
		test_dir = False
		ClassMain = FioMain(io_engine, size_fio, pool_fio, hosts)
		fio_cmd = ClassMain.create_fio_command(block_size, test_mode, num_jobs, io_depth, test_dir)
		fio_expected_cmd = 'fio --name=fio-test --ioengine=rbd --pool=cold-storage --rbdname=$HOSTNAME --iodepth=32 --rw=randwrite --bs=4096k --direct=0 --size=50M --numjobs=4'
		self.assertEqual(fio_cmd, fio_expected_cmd)
		io_engine = ''
		ClassMain = FioMain(io_engine, size_fio, pool_fio, hosts)
		prepare_cmd = ClassMain.prepare_run()
		self.assertEqual(prepare_cmd, None)
		clean_cmd = ClassMain.clean_run()
		self.assertEqual(clean_cmd, None)

class FioMain():
	def __init__(self, io_engine, size_fio, pool_fio, hosts):
		self.ioengine = io_engine
		self.sizefio = size_fio
		self.poolfio = pool_fio
		self.hosts = hosts

	def create_fio_command(self, block_size, test_mode, num_jobs, io_depth, test_dir):
		command = "fio --name=fio-test --ioengine="+self.ioengine+" "
		if self.poolfio:
			command += "--pool="+self.poolfio+" "
		if self.ioengine == "rbd":
			command += "--rbdname=$HOSTNAME "
		if test_dir:
			command += "--directory="+test_dir+" "
		command += "--iodepth="+io_depth+" --rw="+test_mode+" --bs="+block_size+"k --direct=0 --size="+self.sizefio+"M --numjobs="+num_jobs
		return command

	def prepare_run(self):
		if self.ioengine == 'rbd':
			command = "rbd create $HOSTNAME --size "+self.sizefio+" -k /etc/ceph/ceph.client.admin.keyring --pool "+self.poolfio
			run = self.run_command(command)
			return self.check_exit(run)

	def clean_run(self):
		if self.ioengine == 'rbd':
			command = "rbd rm $HOSTNAME --pool "+self.poolfio
			run = self.run_command(command)
			return self.check_exit(run)

	def check_exit(self, output):
		for host in output:
			if output[host]['exit_code'] !=0 :
				return True
				break
		return False

	def run_fio(self, block_size, test_mode, num_jobs, io_depth, test_dir):
		command2 = self.create_fio_command(block_size, test_mode, num_jobs, io_depth, test_dir)
		run = self.run_command(command2)
		if self.check_exit(run):
			aggregate = self.print_global_results(run)
			totbw = self.aggregate_results(aggregate)
			return totbw
			
	def print_global_results(self, output):
		aggregate = {}
		for host in output:
			for line in output[host]['stdout']:
				pattern = re.compile("^WRITE: io=|^READ: io=")
				if pattern.match(line):
					aggregate[host]=line
					print "Host %s - output: %s" % (host, line)
		return aggregate

	def aggregate_results(self, aggregate):
		n=0
		for host in aggregate:
			str = aggregate[host]
			m = re.search("(?:aggrb=([0-9]+))",str).group(1)
			n = n+int(m)
		print "Total bandwidth aggregate=%sKB/s" % n
		return n

	def run_command (self, command):
		client_key = paramiko.RSAKey.from_private_key_file('/root/.ssh/id_rsa')
		client = ParallelSSHClient(self.hosts, pkey=client_key)
		output = client.run_command(command)
		client.pool.join()
		return output

def main(argv):
	config = ConfigParser.RawConfigParser(allow_no_value=True)
	config.readfp(open('pfio.cfg'))
	block_size = config.get("general", "block_size")
	test_mode = config.get("general", "test_mode")
	size_fio = config.get("general", "size_fio")
	pool_fio = config.get("general", "pool_fio")
	num_jobs = config.get("general", "num_jobs")
	hosts = config.get("general", "hosts").split(",")
	io_engine = config.get("general", "io_engine")
	io_depth = config.get("general", "io_depth")
	test_dir = config.get("general", "test_dir")
 
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
			ClassTest = FioTestCase()
			ClassTest.runTest()
			sys.exit()
	ClassMain = FioMain(io_engine, size_fio, pool_fio, hosts)
	if ClassMain.prepare_run():
		print 'error preparing'
	ClassMain.run_fio(block_size, test_mode, num_jobs, io_depth, test_dir)
	if ClassMain.clean_run():
		print 'error cleaning'

if __name__ == "__main__":
	main(sys.argv[1:])
