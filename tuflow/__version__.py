import os
dir = os.path.dirname(__file__)


def version():
	# initialise
	build_type = 'developmental'  # release / developmental
	build_vers = ''
	# read version and build type from metadata.txt
	# means there's only one location to update version
	metadata = os.path.join(dir, 'metadata.txt')
	with open(metadata, 'r') as fo:
		for line in fo:
			if 'version=' in line.lower():
				a, b = line.split('=')
				a = a.strip()
				b = b.strip()
				build_vers = b
			elif 'experimental=' in line.lower():
				a, b = line.split('=')
				a = a.strip()
				b = b.strip()
				if b.lower() == 'false':
					build_type = 'release'
				else:
					build_type = 'developmental'
					
	return build_type, build_vers

