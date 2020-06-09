"""Contains application manager."""

import argparse
import datetime as dt
import os
import re
import subprocess as sp
import sys

from .api import Operator
from .config import config
from .db import db
from .logger import logger
from .utils import locate


class Manager():
    """Represents application manager which is a common CLI."""

    def __init__(self):
        self.root = locate()
        self.operator = Operator()

        args = self._parse_arguments()
        self.sure = args.sure
        self.wait = args.wait
        self.output = args.output
        self.error = args.error

        logger.configure(file=False, format='[{rectype}] {message}\n',
                         alarming=False)

        # If argv more than one then command was entered.
        argv = [arg for arg in sys.argv if arg.startswith('-') is False]
        if len(argv) == 1:
            self.help()
        elif len(argv) == 2 and argv[1] == 'help':
            self.help()
        elif len(argv) > 2 and argv[-1] == 'help':
            name = '_'.join(argv[1:3])
            self.help(name=name)
        elif len(argv) > 2:
            # Read command. Command length is two words as maximum.
            try:
                name = '_'.join(argv[1:3])
                args = argv[3:] if len(argv) > 3 else []
                func = getattr(self, name)
            except AttributeError:
                self.unknown()
            else:
                try:
                    func(*args)
                except TypeError as e:
                    if (
                        e.args[0].startswith(f'{name}() takes')
                        or e.args[0].startswith(f'{name}() missing')
                       ):
                        self.incorrect(name)
                    else:
                        logger.error()
                except Exception:
                    logger.error()

        pass

    def help(self, name=None):
        """Show help note for all available commands."""
        if name == 'help' or name is None:
            funcs = ['create_scheduler', 'start_scheduler', 'stop_scheduler',
                     'restart_scheduler',
                     'create_job', 'edit_script',
                     'configure_job',
                     'enable_job', 'disable_job', 'delete_job',
                     'list_jobs',
                     'run_job', 'run_jobs', 'cancel_job', 'cancel_jobs',
                     'cancel_run',
                     'create_config', 'edit_config',
                     'create_repo', 'sync_repo']
            docs = {}
            for func in funcs:
                doc = getattr(self, func).__doc__.splitlines()[0]
                docs[func] = doc
            demo = os.path.join(os.path.dirname(__file__), 'demo/cli.txt')
            text = open(demo, 'r').read().format(**docs)
            print(text)
        elif name in dir(self):
            func = getattr(self, name)
            text = func.__doc__
            print(text)
        else:
            self.unknown()
        pass

    def incorrect(self, name):
        """Print message about incorrect command."""
        name = name.replace('_', ' ')
        print(f'Incorrect command. Type *{name} help* to see details.')
        pass

    def unknown(self):
        """Print message about unknown command."""
        print('Unknown command. Type *help* to get list of commands.')
        pass

    def create_scheduler(self):
        """Create scheduler in current location."""
        print('Please follow the steps to create the scheduler.')
        name = input('Enter the name or leave empty:\n')
        desc = input('Enter the description or leave empty:\n')
        self.operator.create_scheduler(name=name, desc=desc)
        print('Scheduler created in current location.')
        pass

    def start_scheduler(self):
        """Start scheduler."""
        pid = self.operator.start_scheduler()
        if pid is not None:
            print(f'Scheduler started (PID {pid}).')
        else:
            print('Scheduler failed to start')
        pass

    def stop_scheduler(self):
        """Stop scheduler."""
        self.operator.stop_scheduler()
        print('Scheduler stopped.')
        pass

    def restart_scheduler(self):
        """Restart scheduler."""
        self.stop_scheduler()
        self.start_scheduler()
        print('Scheduler restarted.')
        pass

    def report_scheduler(self):
        """Show current scheduler status."""
        pid = self.operator.report_scheduler()
        if pid is not None:
            print(f'Scheduler is running (PID {pid}).')
        else:
            print('Scheduler is not running.')
        pass

    def create_job(self, scenario=None):
        """Create job in scheduler of current location."""
        if scenario is None:
            print('Please follow the steps to create the job.')
            configuration = self._configure_job()
        while True:
            sure = input('Are you sure? [Y/n] ')
            if sure in ('Y', 'n'):
                break
        if sure == 'Y':
            print('Creating job...')
            if scenario is None:
                id = self.operator.create_job(**configuration)
            elif scenario == 'default':
                id = self.operator.create_job()
            print(f'Job created (ID {id}).')
        else:
            print('Operation canceled.')
        pass

    def configure_job(self, id):
        """Configure job data in schedule table."""
        id = self._check_id(id)
        print('Please follow the steps to configure the job.')
        configuration = self._configure_job()
        while True:
            sure = input('Are you sure? [Y/n] ')
            if sure in ('Y', 'n'):
                break

        if sure == 'Y':
            print('Editing job...')
            self.operator.configure_job(id, **configuration)
            print('Job edited.')
        else:
            print('Operation canceled.')
        pass

    def edit_script(self, id):
        """Open job script in text editor."""
        id = self._check_id(id)
        editor = config['GENERAL'].get('editor')
        path = os.path.join(self.root, f'jobs/{id}/script.py')
        if os.path.exists(path) is True:
            # Launch edition process and wait until it is completed.
            proc = sp.Popen([editor, path])
            print(f'Editing {path}...')
            proc.wait()
        else:
            print(f'File {path} does not exists.')
        pass

    def enable_job(self, id):
        """Activate job."""
        id = self._check_id(id)
        result = self.operator.enable_job(id)
        if result is True:
            print(f'Job enabled (ID {id}).')
        else:
            print(f'Job does not exist (ID {id}).')
        pass

    def disable_job(self, id):
        """Deactivate job."""
        id = self._check_id(id)
        result = self.operator.disable_job(id)
        if result is True:
            print(f'Job disabled (ID {id}).')
        else:
            print(f'Job does not exist (ID {id}).')
        pass

    def delete_job(self, id):
        """Delete job."""
        id = self._check_id(id)
        repr = f'Job[{id}]'
        print(f'You are trying to delete {repr}...')
        sure = input('Are you sure? [delete] ')
        sure = True if sure == 'delete' else False
        if sure is True:
            print(f'{repr} delete confirmed.')
            try:
                self.operator.delete_job(id)
            except Exception:
                print(f'{repr} deleted with errors.')
            else:
                print(f'{repr} deleted.')
        else:
            print(f'{repr} delete was not confirmed.')
        pass

    def list_jobs(self, id=None):
        """Show all scheduled jobs."""
        id = self._check_id(id) if id is not None else id
        jobs = list(self.operator.list_jobs(id=id))
        row = '{id:<5}|{name:<30}|{desc:<30}|{status:<6}|'
        head = row.format(id='ID', name='NAME', desc='DESC', status='STATUS')
        border = 75*'-'
        print(border)
        print(head)
        for job in jobs:
            id = job['id']
            name = job['job_name'] or ''
            desc = job['job_desc'] or ''
            status = job['status'] or ''
            print(border)
            print(row.format(id=id, name=name, desc=desc, status=status))
        print(border)
        pass

    def run_job(self, id, *args):
        """Run one chosen job."""
        id = self._check_id(id)
        repr = f'Job[{id}]'
        ln = len(args)
        keys = ('run', 'date', 'trigger')
        key = args[0] if ln > 1 and args[0] in keys else None
        value = args[1] if ln > 1 and key is not None else None
        kwargs = {}
        if key is not None and value is not None:
            if key in ('run', 'trigger'):
                value = int(value)
            elif key == 'date':
                value = dt.datetime.fromisoformat(value)
            kwargs[key] = value
        kwargs['debug'] = True if 'debug' in args else None
        kwargs['noalarm'] = False if 'noalarm' in args else None
        kwargs['solo'] = True if 'solo' in args else None

        if key is None:
            print(f'You are trying to start {repr} for current date...')
        elif key == 'run':
            print(f'You are trying to start {repr} as Run[{value}]...')
        elif key == 'date':
            print(f'You are trying to start {repr} for date {value}...')
        elif key == 'trigger':
            print(f'You are trying to trigger {repr} from Run[{value}]...')
        sure = self.sure
        if sure is False:
            while True:
                sure = input(f'Are you sure? [Y/n] ')
                if sure in ('Y', 'n'):
                    sure = True if sure == 'Y' else False
                    break
        if sure is True:
            proc = self.operator.run_job(id, wait=False, **kwargs)
            now = dt.datetime.now()
            date = '%Y-%m-%d %H:%M:%S'
            print(f'{repr} started (PID {proc.pid}, {now:{date}}).')
            if self.wait is True:
                print(f'Waiting for {repr} to finish...')
                try:
                    proc.wait()
                except KeyboardInterrupt:
                    now = dt.datetime.now()
                    print(f'\n{repr} canceled, {now:{date}}.')
                else:
                    now = dt.datetime.now()
                    if proc.returncode > 0:
                        print(f'{repr} completed with error, {now:{date}}.')
                        if self.error is True:
                            print(proc.stderr.read().decode())
                    else:
                        print(f'{repr} completed, {now:{date}}.')
                        if self.output is True:
                            print(proc.stdout.read().decode())
        pass

    def run_jobs(self, path=None):
        """Run many jobs."""
        path = os.path.abspath(path or 'run.list')
        if os.path.exists(path) is True:
            for row in open(path, 'r').readlines():
                row = row.split()
                ln = len(row)
                if ln >= 1:
                    id = row[0]
                    args = row[1:] if ln > 1 else []
                    self.run_job(id, *args)
            clean = input(f'Clean file {path}? [Y] ')
            if clean == 'Y':
                open(path, 'w').close()
        pass

    def cancel_job(self, id):
        """Cancel one chosen job runs."""
        id = self._check_id(id)
        repr = f'Job[{id}]'
        print(f'You are trying to cancel all {repr} runs...')
        sure = self.sure
        if sure is False:
            while True:
                sure = input(f'Are you sure? [Y/n] ')
                if sure in ('Y', 'n'):
                    sure = True if sure == 'Y' else False
                    break
        if sure is True:
            self.operator.cancel_job(id)
            print(f'All {repr} runs canceled.')
        pass

    def cancel_jobs(self):
        """Cancel all currently running jobs."""
        print(f'You are trying to cancel all currently running jobs...')
        sure = self.sure
        if sure is False:
            while True:
                sure = input(f'Are you sure? [Y/n] ')
                if sure in ('Y', 'n'):
                    sure = True if sure == 'Y' else False
                    break
        if sure is True:
            self.operator.cancel_jobs()
            print(f'All jobs canceled.')
        pass

    def cancel_run(self, id):
        """Cancel run using its ID."""
        id = self._check_id(id)
        repr = f'Run[{id}]'
        print(f'You are trying to cancel {repr}...')
        sure = self.sure
        if sure is False:
            while True:
                sure = input(f'Are you sure? [Y/n] ')
                if sure in ('Y', 'n'):
                    sure = True if sure == 'Y' else False
                    break
        if sure is True:
            self.operator.cancel_run(id)
            print(f'{repr} canceled.')
        pass

    def create_config(self):
        """Create global configuration file."""
        config_path = self.operator.create_config()
        if config_path is not None:
            print(f'Global config created ({config_path}).')
        else:
            print('Global config was not created.')
        pass

    def edit_config(self, type=None):
        """Open chosen configuration file in text editor."""
        editor = config['GENERAL'].get('editor')
        if type == 'local' or type is None:
            from .config import local_config as path
        elif type == 'global':
            from .config import user_config as path
        elif type.isdigit() is True:
            id = self._check_id(type)
            path = os.path.join(self.root, f'jobs/{id}/devoe.ini')
        path = os.path.abspath(path)
        if os.path.exists(path) is True:
            # Launch edition process and wait until it is completed.
            proc = sp.Popen([editor, path])
            print(f'Editing {path}...')
            proc.wait()
        else:
            print(f'File {path} does not exists.')
        pass

    def create_repo(self):
        """Create job repository and publish it by URL."""
        url = input('Please give remote Git repository URL: ')
        if self.sure is False:
            while True:
                sure = input(f'Are you sure? [Y/n] ')
                if sure in ('Y', 'n'):
                    sure = True if sure == 'Y' else False
                    break
        if sure is True:
            self.operator.create_repo(url=url)
            print('Job repository successfully created.')
        pass

    def sync_repo(self, id=None):
        """Synchronize job repository."""
        print('You are trying to synchronize job repository...')
        sure = self.sure
        if sure is False:
            while True:
                sure = input(f'Are you sure? [Y/n] ')
                if sure in ('Y', 'n'):
                    sure = True if sure == 'Y' else False
                    break
        if sure is True:
            self.operator.pull_repo()
            kwargs = {}
            if id is not None:
                kwargs['id'] = int(id)
            self.operator.push_repo(**kwargs)
            print('Job repository successfully synchronized.')
        pass

    def _parse_arguments(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-y', '--yes', dest='sure', action='store_true',
                            required=False, help='do not ask to confirm')
        parser.add_argument('-w', '--wait', dest='wait', action='store_true',
                            required=False, help='wait for job to finish')
        parser.add_argument('-o', '--output', dest='output',
                            action='store_true', required=False,
                            help='show process stdout')
        parser.add_argument('-e', '--error', dest='error',
                            action='store_true', required=False,
                            help='show process stderr')
        args, anons = parser.parse_known_args()
        return args

    def _configure_job(self):
        name = input('Name this job:\n') or None
        desc = input('Describe shortly this job:\n') or None
        env = input('Enter the environment or leave empty to use default: ')
        env = env or None
        print()
        print('Schedule this job:')
        mday = input('Month day [1-31] == ') or None
        wday = input('Week day [1-7] ==== ') or None
        hour = input('Hour [0-23] ======= ') or None
        min = input('Minute [0-59] ===== ') or None
        sec = input('Second [0-59] ===== ') or None
        trigger = input('Trigger [1...n] === ')
        trigger = int(trigger) if trigger.isdigit() is True else None
        trigger = db.null if trigger == 0 else trigger
        print()
        start_date = input('Start date [YYYY-MM-DD HH24:MI:SS] ') or None
        start_date = db.null if start_date == '-' else None
        end_date = input('End date [YYYY-MM-DD HH24:MI:SS] ') or None
        end_date = db.null if end_date == '-' else None
        print()
        timeout = input('Set timeout [1...n] ')
        timeout = int(timeout) if timeout.isdigit() is True else None
        timeout = db.null if timeout == 0 else timeout
        reruns = input('Limit of reruns number [1...n] ')
        reruns = int(reruns) if reruns.isdigit() is True else None
        reruns = db.null if reruns == 0 else reruns
        days_rerun = input('Limit of days in rerun [1...n] ')
        days_rerun = int(days_rerun) if days_rerun.isdigit() is True else None
        days_rerun = db.null if days_rerun == 0 else days_rerun
        print()
        alarm = input('Enable alarming for this job [Y] ')
        alarm = True if alarm == 'Y' else None
        persons = input('List notification email addresses [a,b,...]: ')
        pattern = r'([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)'
        persons = ','.join(re.findall(pattern, persons)) or None
        result = {'name': name, 'desc': desc, 'env': env,
                  'mday': mday, 'wday': wday,
                  'hour': hour, 'sec': sec, 'min': min,
                  'trigger': trigger,
                  'start_date': start_date, 'end_date': end_date,
                  'timeout': timeout,
                  'reruns': reruns, 'days_rerun': days_rerun,
                  'alarm': alarm, 'persons': persons}
        print()
        return result

    def _check_id(self, id):
        if id.isdigit() is True:
            return int(id)
        else:
            raise TypeError('id must be digit')
        pass