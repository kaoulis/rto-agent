import os
import time
import zipfile
from multiprocessing import Process
import werkzeug
import docker
from flask import Flask, Blueprint
from flask_restx import Resource, Api, Namespace
from os import environ



def create_app() -> Flask:
    app = Flask(__name__)
    # app.config['SQLALCHEMY_DATABASE_URI'] = environ['rto_db_uri']
    # app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # app.config['SCHEDULER_TIMEZONE'] = "Europe/Athens"
    # db.init_app(app)
    app.app_context().push()

    return app


api = Namespace('RTO Agent', description='RTO CI/CD related services')
post_release_parser = api.parser()
post_release_parser.add_argument('release', type=werkzeug.datastructures.FileStorage, required=True, help='The compressed code', location='files')
post_release_parser.add_argument('volume_path', type=str, required=True, help='The volume path', location='form')
post_release_parser.add_argument('image_name', type=str, required=True, help='The image name', location='form')

@api.route('/deploy')
class Deploy(Resource):
    deployment_processes: list[Process] = []

    @api.doc(parser=post_release_parser)
    @api.response(200, 'Deployment was started successful!')
    @api.response(401, 'Unauthorized.')
    def post(self):
        args = post_release_parser.parse_args()

        release = args['release']
        volume_path = args['volume_path']
        image_name = args['image_name']

        if not os.path.exists(volume_path):
            os.makedirs(volume_path)

        # TODO: Backup previous version

        # FIXME: exclude logs file replacement
        with zipfile.ZipFile(release, 'r') as zip_ref:
            zip_ref.extractall(volume_path)

        # Manage deployment process
        for p in self.deployment_processes:
            p.terminate()
            print(f'Terminating previous deployment process..')
            while p.is_alive():
                pass
            print(f'Previous deployment process was terminated successfully!')
            self.deployment_processes.remove(p)

        deployment_process = Process(target=deployment_task, args=(image_name,), daemon=True)
        deployment_process.start()
        self.deployment_processes.append(deployment_process)

        response = {'message': 'Deployment was started successfully (code 200)!'}
        print(response['message'])

        return response


def deployment_task(image_name):
    print('New deployment process in progress..')
    # TODO: Checking RTO selection status to proceed with deployment
    # while True:
    #     time.sleep(30)
    docker_client = docker.from_env()
    try:
        containers = docker_client.containers.list(all=True, filters={'ancestor': image_name})
        if not containers:
            raise f"Image '{image_name}' not found."
        # Restart each container
        for container in containers:
            print(f"Restarting container '{container.name}' in progress..")
            container.restart()
            print(f"Container '{container.name}' restarted successfully.")
    except docker.errors.APIError as e:
        print(f"Error restarting containers of '{image_name}': {e}")
    print('Deployment was successful!')



blueprint = Blueprint('api', __name__)

swagger = Api(
    blueprint,
    title='RTO Agent API',
    version='1.0',
    description='RTO Agent Services',
)

swagger.add_namespace(api, path='/agent')
app = create_app()
app.register_blueprint(blueprint)
app.app_context().push()

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    app.run(host='0.0.0.0', port=12600)
