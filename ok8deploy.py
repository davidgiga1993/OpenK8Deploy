from __future__ import annotations

import argparse
import os

from config.Config import ProjectConfig
from deploy.AppDeploy import AppDeployment


def reload_config(args):
    root_config = ProjectConfig.load(args.config_dir)
    app_config = root_config.load_app_config(args.name[0])
    if not app_config.enabled():
        print('App is disabled')
        return
    if app_config.is_template():
        print('App is a template')
        return

    oc = root_config.create_oc()
    print('Reloading ' + app_config.get_dc_name())
    reload_actions = app_config.get_reload_actions()
    for action in reload_actions:
        action.run(oc)
    print('Done')


def plan_app(args):
    args.out_file = None
    args.dry_run = True
    deploy_app(args)


def plan_all(args):
    args.out_file = None
    args.dry_run = True
    deploy_all(args)


def deploy_app(args):
    root_config = ProjectConfig.load(args.config_dir)
    app_config = root_config.load_app_config(args.name[0])

    deployment = AppDeployment(root_config, app_config, out_file=args.out_file, dry_run=args.dry_run)
    deployment.deploy()
    print('Done')


def deploy_all(args):
    base_dir = args.config_dir
    root_config = ProjectConfig.load(base_dir)
    for dir_item in os.listdir(base_dir):
        path = os.path.join(base_dir, dir_item)
        if not os.path.isdir(path):
            continue

        try:
            app_config = root_config.load_app_config(dir_item)
        except FileNotFoundError:
            # Index file missing
            continue

        if app_config.is_template() or not app_config.enabled():
            # Silently skip
            continue

        AppDeployment(root_config, app_config, dry_run=args.dry_run).deploy()
    print('Done')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-dir', dest='config_dir', help='Path to the folder containing all configurations',
                        default='../configs')

    subparsers = parser.add_subparsers(help='Commands')
    reload_parser = subparsers.add_parser('reload', help='Reloads the configuration of a running application')
    reload_parser.add_argument('name', help='Name of the app which should be reloaded (folder name)', nargs=1)
    reload_parser.set_defaults(func=reload_config)

    plan_parser = subparsers.add_parser('plan', help='Verifies what changes have to be applied for a single app')
    plan_parser.add_argument('name', help='Name of the app which should be checked (folder name)', nargs=1)
    plan_parser.set_defaults(func=plan_app)

    plan_all_parser = subparsers.add_parser('plan-all',
                                            help='Verifies what changes have to be applied for a single app')
    plan_all_parser.set_defaults(func=plan_all)

    deploy_parser = subparsers.add_parser('deploy', help='Deploys the configuration of an application')
    deploy_parser.add_argument('--out-file', dest='out_file',
                               help='Writes all objects into a yml file instead of deploying them. '
                                    'This does not communicate with openshift in any way')
    deploy_parser.add_argument('--dry-run', dest='dry_run', help='Does not interact with openshift',
                               action='store_true')
    deploy_parser.add_argument('name', help='Name of the app which should be deployed (folder name)', nargs=1)
    deploy_parser.set_defaults(func=deploy_app)

    deploy_all_parser = subparsers.add_parser('deploy-all',
                                              help='Deploys all objects of all enabled application')
    deploy_all_parser.set_defaults(func=deploy_all)

    args = parser.parse_args()
    if 'func' not in args.__dict__:
        parser.print_help()
        exit(1)
        return

    args.func(args)


if __name__ == '__main__':
    main()
