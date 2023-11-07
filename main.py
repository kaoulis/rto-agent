import werkzeug
import docker
from flask import Flask
from flask_restx import Resource, Api

app = Flask(__name__)
api = Api(app)

docker_client = docker.from_env()


post_image_parser = api.parser()
post_image_parser.add_argument('image_tar', type=werkzeug.datastructures.FileStorage, location='files')

@api.route('/hello')
class HelloWorld(Resource):

    @api.doc(parser=post_image_parser)
    @api.response(201, 'Deployment was successful!')
    @api.response(401, 'Unauthorized.')
    def post(self):
        data = post_image_parser.parse_args()
        if 'image_tar' not in data:
            return {'message': 'No image file provided'}, 400

        image_file = data['image_tar']

        try:
            docker_client.images.load(image_file.stream.read())
            # return {'message': 'Docker image loaded successfully'}
        except Exception as e:
            return {'error': str(e)}, 500

        # Run a container from the loaded image
        try:
            container = docker_client.containers.run(
                'cmo-dashboard-api:latest',  # Replace with the actual image name and tag
                detach=True  # Run the container in the background
            )
            return {'message': 'Docker image loaded and container started successfully'}
        except Exception as e:
            return {'error': str(e)}, 500



if __name__ == '__main__':
    app.run(debug=True)
