# -*- coding: utf-8 -*-

from os import mkdir
from os.path import abspath, basename, dirname, join, getsize
from shutil import copyfile, rmtree

from django.test import TestCase
from django.test.client import Client

from django.conf import settings
from django.contrib.auth.models import User

from tardis.tardis_portal.models import Experiment, Dataset, Dataset_File
from tardis.tardis_portal.logger import logger


class DownloadTestCase(TestCase):

    def setUp(self):
        # create a test user
        self.user = User.objects.create_user(username='DownloadTestUser',
                                             email='',
                                             password='secret')

        # create a public experiment
        self.experiment1 = Experiment(title='Experiment 1',
                                      created_by=self.user,
                                      public=True)
        self.experiment1.save()

        # create a non-public experiment
        self.experiment2 = Experiment(title='Experiment 2',
                                      created_by=self.user,
                                      public=False)
        self.experiment2.save()

        # dataset1 belongs to experiment1
        self.dataset1 = Dataset(experiment=self.experiment1)
        self.dataset1.save()

        # dataset2 belongs to experiment2
        self.dataset2 = Dataset(experiment=self.experiment2)
        self.dataset2.save()

        # absolute path first
        filename = 'testfile.txt'
        self.dest1 = abspath(join(settings.FILE_STORE_PATH, '%s' % self.experiment1.id))
        self.dest2 = abspath(join(settings.FILE_STORE_PATH, '%s' % self.experiment2.id))

        mkdir(self.dest1)
        mkdir(self.dest2)

        testfile1 = abspath(join(self.dest1, filename))
        f = open(testfile1, 'w')
        f.write("Hello World!\n")
        f.close()

        testfile2 = abspath(join(self.dest2, filename))
        f = open(testfile2, 'w')
        f.write("Hello World!\n")
        f.close()

        self.dataset_file1 = Dataset_File(dataset=self.dataset1,
                                          filename=filename,
                                          protocol='tardis',
                                          url='tardis://%s' % filename)
        self.dataset_file1.save()

        self.dataset_file2 = Dataset_File(dataset=self.dataset2,
                                          filename=basename(filename),
                                          protocol='tardis',
                                          url='tardis://%s' % filename)
        self.dataset_file2.save()

        # check pdf mimetype
        # self.dataset_file3 = ...

    def tearDown(self):
        self.user.delete()
        self.experiment1.delete()
        self.experiment2.delete()
        rmtree(self.dest1)
        rmtree(self.dest2)

    def testDownload(self):
        client = Client()

        # check download for experiment1
        response = client.get('/download/experiment/%i/' % self.experiment1.id)
        self.assertEqual(response['Content-Disposition'],
                         'attachment; filename="experiment%s-complete.tar"' % self.experiment1.id)
        self.assertEqual(response.status_code, 200)

        # check download of file1
        response = client.get('/download/datafile/%i/' % self.dataset_file1.id)
        self.assertEqual(response['Content-Disposition'],
                         'attachment; filename="%s"' % self.dataset_file2.filename)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'Hello World!\n')

        # requesting file2 should be forbidden...
        response = client.get('/download/datafile/%i/' % self.dataset_file2.id)
        self.assertEqual(response.status_code, 403)

        # check dataset1 download
        response = client.post('/download/datafiles/',
                               {'expid': self.experiment1.id,
                                'dataset': [self.dataset1.id],
                                'datafile': []})
        self.assertEqual(response.status_code, 200)

        # check dataset2 download
        response = client.post('/download/datafiles/',
                               {'expid': self.experiment2.id,
                                'dataset': [self.dataset2.id],
                                'datafile': []})
        self.assertEqual(response.status_code, 403)

        # check datafile1 download via POST
        response = client.post('/download/datafiles/',
                               {'expid': self.experiment1.id,
                                'dataset': [],
                                'datafile': [self.dataset_file1.id]})
        self.assertEqual(response.status_code, 200)

        # check datafile2 download via POST
        response = client.post('/download/datafiles/',
                               {'expid': self.experiment2.id,
                                'dataset': [],
                                'datafile': [self.dataset_file2.id]})
        self.assertEqual(response.status_code, 403)

    def testDatasetFile(self):
        df = Dataset_File.objects.get(pk=self.dataset_file1.id)

        self.assertEqual(df.mimetype, u'text/plain; charset=us-ascii')
        self.assertEqual(df.size, str(13))
        self.assertEqual(df.md5sum, u'8ddd8be4b179a529afa5f2ffae4b9858')

