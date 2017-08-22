#!/usr/bin/env python
# coding: utf-8

import os
import time
import argparse
from configparser import ConfigParser
import datetime
import shutil

def parseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--main_config", help="main config file, user-specific",\
                          type=str ,default='default.cfg')
    parser.add_argument("--project", help="The name for the Project", type=str ,default='some_NN')
    parser.add_argument("--input", help="Name of the input files seperated by :", type=str ,default='all')
    parser.add_argument("--model", help="Name of the File containing the model", type=str, default='simple_CNN.cfg')
    parser.add_argument("--virtual_len", help="Use an artifical array length (for debugging only!)", type=int , default=-1)
    parser.add_argument("--continue", help="Give a folder to continue the training of the network", type=str, default = 'None')
    parser.add_argument("--version", action="version", version='%(prog)s - Version 1.0')
    args = parser.parse_args()
    return args

def make_condor(request_gpus, request_memory, requirements, addpath,\
                file_location, arguments, thisfolder):
    submit_info = '\
            executable   = {6}/Neural_Network.py \n\
            universe     = vanilla  \n\
            request_gpus = {0} \n\
            request_memory = {1}GB \n\
            requirements = {2} \n\
            log          = {3}/condor.log \n\
            output       = {3}/condor.out \n\
            error        = {3}/condor.err \n\
            stream_output = True \n\
            getenv = True \n\
            IWD = {4} \n\
            arguments =  {5} \n\
            queue 1 \n '.format(request_gpus, \
                                request_memory, requirements, addpath,\
                                file_location, arguments, thisfolder)
    return submit_info

def make_slurm(request_gpus, request_memory, addpath, file_location,\
               arguments,thisfolder):
##SBATCH --exclude=bigbird\n\
 
  submit_info = '\
#!/usr/bin/env bash\n\
#SBATCH --time=24:00:00\n\
#SBATCH --partition=gpu\n\
#SBATCH --gres=gpu:{0}\n\
#SBATCH --mem={1} \n\
#SBATCH --error={2}/condor.err\n\
#SBATCH --output={2}/condor.out\n\
#SBATCH --workdir={3}\n\
\n\
python {5}/Neural_Network.py {4} \n'.\
format(request_gpus, int(request_memory), addpath, file_location, \
  arguments, thisfolder)

  return submit_info

args = parseArguments().__dict__
parser = ConfigParser()
parser.read(args["main_config"])

file_location = parser.get('Basics', 'train_folder')
workload_manager = parser.get('Basics', 'workload_manager')
request_gpus = parser.get('GPU', 'request_gpus')
request_memory = parser.get('GPU', 'request_memory')
requirements = parser.get('GPU', 'requirements')
project_name = args['project']
thisfolder = parser.get("Basics", "thisfolder")

if workload_manager != 'slurm' and workload_manager != 'condor':
	raise NameError('Workload manager not defined. Should either be condor or slurm!')

if args['input'] == 'lowE':
	files = '11029_00000-00999.h5:11029_01000-01999.h5:11029_02000-02999.h5:11029_03000-03999.h5:11029_04000-04999.h5:11029_05000-05999.h5'
elif args['input'] == 'highE':
    files = '11069_00000-00999.h5:11069_01000-01999.h5:11069_02000-02999.h5:11069_03000-03999.h5:11069_04000-04999.h5:11069_05000-05999.h5'
else:
	files = args['input']

if args['continue'] != 'None':
    arguments = '--continue {}'.format(args['continue'])
    addpath = args['continue']
    if addpath[-1]=='/':
        addpath = addpath[:-1]

    if workload_manager == 'slurm':
        submit_info = make_slurm(request_gpus, float(request_memory)*1e3, \
                                 addpath, file_location, arguments, thisfolder)
    elif workload_manager == 'condor':
        submit_info = make_condor(request_gpus, request_memory, requirements,\
                            addpath, file_location, arguments, thisfolder)

else:
    today = str(datetime.datetime.now()).replace(" ","-").split(".")[0].\
            replace(":","-")
    folders = ['{}'.format(project_name),
             '{}/{}'.format(project_name, today),
             '{}/{}/condor/'.format(project_name, today)]
    for folder in folders:
        if not os.path.exists('{}'.format(os.path.join(file_location,folder))):
            print('Create Folder {}'.format(os.path.join(file_location,folder)))
            os.makedirs('{}'.format(os.path.join(file_location,folder)))

	arguments = ''
    for a in args:
        if not a == 'input':
            arguments += '--{} {} '.format(a, args[a])
        else:
            arguments += '--input {} '.format(files)
    print("\n --------- \n You are running the script with arguments: \n {}  \
		\n --------- \n").format(arguments)

    arguments += '--date {} '.format(today)
    arguments += '--ngpus {} '.format(request_gpus)
    addpath = os.path.join(file_location,'{}/{}/condor/'.\
                           format(project_name, today))

    if workload_manager == 'slurm':
        submit_info = make_slurm(request_gpus, float(request_memory)*1e3,\
                                 addpath, file_location, arguments, thisfolder)
    elif workload_manager == 'condor':
		submit_info = make_condor(request_gpus, request_memory, requirements,\
                            addpath, file_location, arguments, thisfolder)

print(submit_info)

submitfile_full = file_location+'{}/{}/condor/submit.sub'.\
        format(project_name, today)
with open(submitfile_full, "wc") as file:
    file.write(submit_info)

os.system("cp {} {}/{}/{}/".format(args["main_config"], file_location,\
                                  project_name, today))

os.system("cp {} {}/{}/{}/".format(args["model"], file_location,\
                                  project_name, today))


if workload_manager == 'slurm':
	os.system("sbatch {}".format(submitfile_full))
else:
	os.system("condor_submit {}".format(submitfile_full))

time.sleep(3)


