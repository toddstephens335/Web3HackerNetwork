import os
from db_driven_task import DBDrivenTaskProcessor, DBTask
from shutil import rmtree
from threading import Lock


class RepoCleanup(DBDrivenTaskProcessor):

    class Fetcher(DBTask):
        def __init__(self, mom):
            self.mom = mom

        def get_proc_name(self):
            return 'ReserveNextRepoForCleanup'

        def get_proc_parameters(self):
            return [self.mom.machine_name]

        def process_db_results(self, result_args):
            for goodness in self.mom.cursor.stored_results():
                result = goodness.fetchone()
                if result:
                    self.mom.repo_id = int(result[0])
                    self.mom.repo_owner = result[1]
                    self.mom.repo_name = result[2]
                    self.mom.repo_dir = result[3]
            return result

    class Closer(DBTask):
        def __init__(self, mom):
            self.mom = mom

        def get_proc_name(self):
            return 'ReleaseRepoAfterCleanup'

        def get_proc_parameters(self):
            return [self.mom.repo_id]

        def process_db_results(self, result_args):
            pass

    def __init__(self, lock):
        super().__init__(lock)
        self.repo_id = None
        self.repo_owner = None
        self.repo_name = None
        self.repo_dir = None
        self.fetcher = self.Fetcher(self)
        self.closer = self.Closer(self)

    def get_job_fetching_task(self):
        return self.fetcher

    def get_job_completion_task(self):
        return self.closer

    def process_task(self):
        target_dir = './repos/'+self.repo_owner+'/'+self.repo_name
        print('Removing repo dir '+target_dir)

        if os.path.isdir(target_dir):
            rmtree(target_dir, ignore_errors=True)
            if len(os.listdir('./repos/'+self.repo_owner)) < 1:
                print('Removing empty parent repo dir '+self.repo_owner)
                os.rmdir('./repos/'+self.repo_owner)
        else:
            print('Or not... Could NOT find '+target_dir)


if __name__ == "__main__":
    RepoCleanup(Lock()).main()