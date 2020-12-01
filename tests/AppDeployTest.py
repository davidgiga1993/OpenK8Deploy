import os
from unittest import TestCase

import yaml

from config.Config import RootConfig
from deploy.AppDeploy import AppDeployRunner
from utils.Errors import MissingParam


class AppDeployTest(TestCase):

    def setUp(self) -> None:
        self._base_path = os.path.dirname(__file__)
        self._tmp_file = 'out.yml'

    def tearDown(self) -> None:
        if os.path.isfile(self._tmp_file):
            os.remove(self._tmp_file)

    def test_params(self):
        root_config = RootConfig.load(os.path.join(self._base_path, 'app_deploy_test'))
        app_config = root_config.load_app_config('app-params')
        runner = AppDeployRunner(root_config, app_config)
        runner.write_file(self._tmp_file)
        try:
            runner.deploy()
            self.fail('No exception raised for missing param')
        except MissingParam:
            pass

        external_params = {
            'SomeParam': 'input'
        }
        app_config._external_vars = external_params
        runner.deploy()

        with open(self._tmp_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        self.assertEqual('input', data['someObj']['param'])

    def test_inherit_vars(self):
        root_config = RootConfig.load(os.path.join(self._base_path, 'app_deploy_test'))
        app_config = root_config.load_app_config('app')
        runner = AppDeployRunner(root_config, app_config)
        runner.write_file(self._tmp_file)
        runner.deploy()

        with open(self._tmp_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        self.assertEqual('ABC', data['metadata']['name'])
        self.assertEqual('DEF', data['metadata']['name2'])
        self.assertEqual('3', data['metadata']['base'])
