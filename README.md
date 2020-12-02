# Openshift/K8 templating and deployment engine
Super simple python templating and deployment engine for openshift/k8 yml files.
Detects changes made and only applies the required objects.

## Use case
This tool was born in the need to a very simple templating system
which can track changes (similar to terraform). It was build for my requirements but should
fit others as well.

## Requirements
- Python 3.8 or later
- `oc` (or `kubectl`) binary in path

## Usage
### Deploy all changes
Deploys all enabled app 
```
python deploy.py deploy-all
```

### Deploy single app
Deploys all object of the app with the give name
```
python deploy.py deploy nginx
```

### Reload config
This command executes the `on-config-change` trigger
```
python deploy.py reload prometheus
```


## Configuration
In OK8Deploy you define apps, each app can contain multiple yml files.
Additionally, there is a project configuration which describes the OC project.

All yml files will be pre-processed before they will be imported.
This includes replacing any known `${KEY}` variables with their associate values.

### Config structure
```
configs
|- _root.yml <- Project config
|- my-app
    |- _index.yml <- App config
    |- dc.yml
    |- secrets.yml
```

### Project config
Here is a sample `_root.yml` file
```yml
project: 'my-oc-project'
```
### App config
A single app is represented by a folder containing an `_index.yml` file as well as any additional openshift yml files.
```yml
# The type defines how the app will be used.
# Can be "app" (default) or "template"
type: 'app'

# Indicates if this app should be deployed or ignored
enabled: true 

# Deployment config parameters
dc:
    # Name of the deployment config, available as variable, see below
    name: 'my-app'

# Template which should be applied, none by default
applyTemplates: []

# Templates which should be applied AFTER processing the other templates and base yml files
postApplyTemplates: []

# OPTIONAL
# Action which should be executed if a configmap has been changed
on-config-change:
# Available options: 
# deploy (re-deploys the deployment config)
  - deploy

# exec (Executes a command inside the running container)
  - exec: 
      command: /bin/sh
      args: 
        - "-c"
        - "kill -HUP $(ps a | grep prometheus | grep -v grep | awk '{print $1}')"

# Additional variables available in the template file
vars:
  NSQ_NAME: 'nsq-core'

# File based configmaps
configmaps:
  - name: nginx-config
    files:
      - file: "nginx.conf"
```

### Configmaps
In addition to the regular configmaps you can also define configmaps with a file source.
This is done in the `_index.yml` file:
```yml
configmaps:
  - name: nginx-config
    files:
      - file: "nginx.conf"
```
This will create a new configmap from the file `nginx.conf` with the name `nginx-config`.
Any changes made to the file will be automatically deployed.

### Variables
You can refer to variables in yml files by using `${VAR-NAME}`

### Global variables
The following variables are available anywhere inside the yml files by default

| Key | Value |
| --- | --- | 
| `DC_NAME` | Name of the deployment-config in the `_index.yml` |


### Templates
You can use templates to generate yml files for openshift.
To do so you create a new app with the `type` field set to `template`.
Other apps can now refer to this template via the `templates` field. The content of a template will then be
processed using the app variables and deployed in addition to any other yml files inside the app directory.

Example:
```
|- some-template
    |- _index.yml
    |- dc.yml

|- my-app
    |- _index.yml
    |- others.yml
```

Will result in
```
|- my-app
    |- _index.yml
    |- others.yml
    |- dc.yml
```

#### Object merging
The template engine support content aware object merging.
This allows you to decorate existing templates or enhance apps with features.
A common example would be a template which adds a monitoring sidecar container.
In the `examples` you can find the `nsq-template` which defines a sidecar container.

Here is a minimal example:
```yml
# examples/nsq-template/dc.yml
kind: DeploymentConfig
apiVersion: v1
spec:
    template:
        spec:
        containers:
            - name: "nsqd"
            image: "nsqio/nsq"
```

```yml
# examples/my-app/dc.yml
kind: DeploymentConfig
apiVersion: v1
metadata:
  name: "${DC_NAME}"

spec:
  replicas: 1
  selector:
    name: "${DC_NAME}"
  strategy:
    type: Rolling

  template:
    metadata:
      labels:
        name: "${DC_NAME}"

    spec:
      containers:
        - name: "${DC_NAME}"
          image: "docker-registry.default.svc:5000/oc-project/my-app:prod"
```

If we now apply the nsq-template to our app using `postApplyTemplates: [nsq-template]` the
`DeploymentConfig` object gets automatically merged:
```yml
# Merged result after applying template
kind: DeploymentConfig
apiVersion: v1
metadata:
  name: "${DC_NAME}"

spec:
  replicas: 1
  selector:
    name: "${DC_NAME}"
  strategy:
    type: Rolling

  template:
    metadata:
      labels:
        name: "${DC_NAME}"

    spec:
      containers:
        - name: "${DC_NAME}"
          image: "docker-registry.default.svc:5000/oc-project/my-app:prod"
        # This is the part of the template
        - name: "nsqd"
            image: "nsqio/nsq"
```

## Change tracking
Changes are detected by storing a md5 sum in the label of the object.
If this hash has changed the whole object will be applied.
If no tabel has been found in openshift the object is assumed to be equal, and the label is added.

## Examples
All examples can be found in the `examples` folder.
### Grafana
The grafana folder contains a basic grafana setup.

### NSQ
This example adds an NSQ sidecar container to a deployment config.


`my-app/_index.yml`
```yml
enabled: true
postApplyTemplates: [nsq-template]
vars:
  NSQ_NAME: 'app-nsq'

dc:
  name: my-app
```



## Contribute
The code should be mostly commented, although I didn't bother implementing proper logging and other utils stuff.
If you found a bug or want to improve something feel free to open an issue and discuss your ideas.