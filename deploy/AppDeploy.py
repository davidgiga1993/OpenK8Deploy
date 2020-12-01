import hashlib
import os
from typing import Optional, List

import yaml

from config.Config import RootConfig, AppConfig
from oc.Oc import Oc
from processing.OcObjectMerge import OcObjectMerge
from processing.YmlTemplateProcessor import YmlTemplateProcessor


class DeployRunner:
    """
    Deploys single yml files
    """

    HASH_ANNOTATION = 'yml-hash'

    def __init__(self, root_config: RootConfig, oc: Oc, app_config: AppConfig):
        self._root_config = root_config  # type: RootConfig
        self._app_config = app_config  # type: AppConfig
        self._oc = oc  # type: Oc

    def deploy_object(self, data: dict):
        """
        Deploy the given object (if a deployment required, otherwise does nothing)
        :param data: Data which should be deployed
        """

        # Sort the content so it's always reproducible
        str_repr = yaml.dump(data, sort_keys=True)
        # Sanity check
        if '${' in str_repr:
            raise ValueError('At least one variable could not been resolved: ' + str_repr)

        hash_val = hashlib.md5(str_repr.encode('utf-8')).hexdigest()

        item_name = data['kind'] + '/' + data['metadata']['name']
        description = self._oc.get(item_name)
        current_hash = None
        if description is not None:
            current_hash = description.get_annotation(self.HASH_ANNOTATION)

        if description is not None and current_hash is None:
            # Item has not been deployed yet with this script, assume both are the same
            print('Updating annotation of ' + item_name)
            self._oc.annotate(item_name, self.HASH_ANNOTATION, hash_val)
            return

        if current_hash == hash_val:
            print(item_name + ' has not been changed')
            return

        print(item_name + ' has changed: Applying update')

        self._oc.apply(str_repr)
        self._oc.annotate(item_name, 'yml-hash', hash_val)

        item_kind = data['kind'].lower()
        if item_kind == 'ConfigMap'.lower():
            self._reload_config()

    def _reload_config(self):
        """
        Tries to reload the configuration for the app
        """
        reload_actions = self._app_config.get_reload_actions()
        for action in reload_actions:
            action.run(self._oc)


class DeploymentBundle:
    """
    Holds all objects of a single deployment
    """

    def __init__(self):
        self.objects = []  # All objects which should be deployed

    def add_object(self, data: dict, template_processor: YmlTemplateProcessor):
        """
        Adds a new object which should be deployed
        :param data: Object
        """
        item_kind = data['kind'].lower()
        if item_kind == 'Secret'.lower():
            print('Secrets are ignored')
            return
        if item_kind == 'PersistentVolumeClaim'.lower():
            print("PVCs are ignored")
            return

        # Pre-process any variables
        template_processor.process(data)

        merger = OcObjectMerge()
        # Check if the new data can be merged into any existing objects
        for item in self.objects:
            if merger.merge(item, data):
                # Data has been merged
                return

        self.objects.append(data)

    def deploy(self, deploy_runner: DeployRunner):
        """
        Deploys all object
        :param deploy_runner: Deployment runner which should be used
        """

        # First sort the objects
        # we want deploymentconfigs to be the last items since a config change might
        # have an impact
        def sorting(x):
            if x['kind'].lower() == 'DeploymentConfig'.lower():
                return 1
            return 0

        self.objects.sort(key=sorting)
        for item in self.objects:
            deploy_runner.deploy_object(item)

    def dump_objects(self, path: str):
        with open(path, 'w') as file:
            yaml.dump_all(self.objects, file, default_flow_style=False, sort_keys=True)


class AppDeployRunner:
    """
    Deploys a complete application
    """

    def __init__(self, root_config: RootConfig, app_config: AppConfig):
        self._root_config = root_config
        self._app_config = app_config
        self._bundle = DeploymentBundle()
        self._write_file = None  # type: Optional[str]

    def write_file(self, path: str):
        self._write_file = path

    def deploy(self):
        """
        Deploys all items for the given app
        """
        if not self._app_config.enabled():
            raise ValueError('App is disabled')
        if self._app_config.is_template():
            raise ValueError('App is a template and can\'t be deployed')

        root_template_processor = YmlTemplateProcessor(self._app_config)
        self._deploy_templates(self._app_config.get_pre_template_refs(), root_template_processor)
        self._load_files(self._app_config.get_config_root(), root_template_processor)
        self._deploy_extra_configmaps(root_template_processor)
        self._deploy_templates(self._app_config.get_post_template_refs(), root_template_processor)

        oc = self._root_config.create_oc()
        deploy_runner = DeployRunner(self._root_config, oc, self._app_config)
        if self._write_file is not None:
            self._bundle.dump_objects(self._write_file)
            return

        oc.project(self._root_config.get_project())
        print('Deploying ' + self._app_config.get_dc_name())
        self._bundle.deploy(deploy_runner)

    def _deploy_templates(self, template_names: List[str], template_processor: YmlTemplateProcessor):
        """
        Deploys all yml files in the referenced template
        """
        for template_name in template_names:
            print('Applying template: ' + template_name)
            template = self._root_config.load_app_config(template_name)
            if not template.is_template():
                raise ValueError('Referenced app ' + template_name + ' is not declared as template')
            if not template.enabled():
                print('Warning: Template ' + template_name + ' is disabled, skipping')
                return

            child_template_processor = YmlTemplateProcessor(template)
            # Inherit all vars from the previous template processor
            child_template_processor.inherit(template_processor)

            # The template might reference other templates
            # -> Recursively deploy them
            self._deploy_templates(template.get_pre_template_refs(), child_template_processor)
            self._load_files(template.get_config_root(), child_template_processor)
            self._deploy_templates(template.get_post_template_refs(), child_template_processor)

    def _load_files(self, root: str, template_processor: YmlTemplateProcessor):
        """
        Loads all yml files inside the given folder
        :param root: Path to the root of the configs folder
        """
        for item in os.listdir(root):
            path = os.path.join(root, item)
            if not os.path.isfile(path) or not item.endswith('.yml') or item.startswith('_'):
                continue

            with open(path, 'r') as stream:
                data = yaml.load_all(stream, Loader=yaml.FullLoader)
                for doc in data:
                    if doc is None:
                        # Empty block
                        continue
                    self._bundle.add_object(doc, template_processor)

    def _deploy_extra_configmaps(self, template_processor: YmlTemplateProcessor):
        for config in self._app_config.get_config_maps():
            oc_obj = config.build_oc_obj(self._app_config.get_config_root())
            self._bundle.add_object(oc_obj, template_processor)
