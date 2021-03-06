import os
import yaml
import json
import requests

from flask import Flask, jsonify
from flask_restful import Api
from flask_jwt_extended import JWTManager

from blacklist import BLACKLIST
from resources.user import UserRegister, User, UserLogin, TokenRefresh, UserLogout
from resources.hospital import HospitalRegister, Hospital, HospitalList
from resources.provider import ProviderRegister, Provider, ProviderList
from resources.request import ResourceRequestRegister, ResourceRequest, ResourceRequestList, ResourceRequestListAll
from resources.supply import ResourceSupplyRegister, ResourceSupply, ResourceSupplyList
from resources.shipment import ShipmentRegister, Shipment, ShipmentList
from resources.resource import ResourceRegister, Resource, ResourceList


def create_app():
    # create the app instance
    app = Flask(__name__)

    CONFIGS = dict

    with open('configs.yml') as configs_file:
        CONFIGS = yaml.load(configs_file, Loader=yaml.FullLoader)

    app.config["MONGO_URI"] = CONFIGS.get(
        "mongo_uri", "mongodb://localhost:27017/CoronaCare?retryWrites=false")

    app.config[
        "PROPAGATE_EXCEPTIONS"
    ] = True  # exceptions are re-raised rather than being handled by app's error handlers
    app.config["JWT_BLACKLIST_ENABLED"] = True  # enable blacklist feature
    app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = [
        "access",
        "refresh",
    ]  # allow blacklisting for access and refresh tokens
    app.config["JWT_SECRET_KEY"] = "secret"  #

    @app.route('/')
    def home():
        return "<h1>CoronaCare API :)<h1/>"

    @app.route('/setup')
    def add_sample_data():
        data = {}
        with open('sample-data.json') as f:
            data = json.load(f)

        for hospital in data.get('hospitals'):
            requests.post(url="http://localhost:5000/hospital", data=hospital)

        for provider in data.get('providers'):
            requests.post(url="http://localhost:5000/provider", data=provider)

        # this is not working for some reason
        for resource in data.get('resources'):
            requests.post(url="http://localhost:5000/resource", data=resource)

        return "It worked!"

    # creates an instance of flask-restful api that will be used to add our resources
    api = Api(app)

    # creates an instance of jwt manager that will handle authentication for the application
    jwt = JWTManager(app)

    # This method will check if a token is blacklisted, and will be called automatically when blacklist is enabled
    @jwt.token_in_blacklist_loader
    def check_if_token_in_blacklist(decrypted_token):
        # Here we blacklist particular JWTs that have been created in the past.
        return decrypted_token["jti"] in BLACKLIST

    # The following callbacks are used for customizing jwt response/error messages for certain situations.
    @jwt.expired_token_loader
    def expired_token_callback():
        return jsonify({"message": "The token has expired.", "error": "token_expired"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return (
            jsonify(
                {"message": "Signature verification failed.", "error": "invalid_token"}
            ),
            401,
        )

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return (
            jsonify(
                {
                    "description": "Request does not contain an access token.",
                    "error": "authorization_required",
                }
            ),
            401,
        )

    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback():
        return (
            jsonify(
                {"description": "The token is not fresh.",
                    "error": "fresh_token_required"}
            ),
            401,
        )

    @jwt.revoked_token_loader
    def revoked_token_callback():
        return (
            jsonify(
                {"description": "The token has been revoked.",
                    "error": "token_revoked"}
            ),
            401,
        )

    # User
    api.add_resource(UserRegister, "/register")
    api.add_resource(User, "/user/<string:username>")
    api.add_resource(UserLogin, "/login")
    api.add_resource(TokenRefresh, "/refresh")
    api.add_resource(UserLogout, "/logout")

    # Hospital
    api.add_resource(HospitalRegister, "/hospital")
    api.add_resource(Hospital, "/hospital/<string:_id>")
    api.add_resource(HospitalList, "/hospitallist")

    # Provider
    api.add_resource(ProviderRegister, "/provider")
    api.add_resource(Provider, "/provider/<string:_id>")
    api.add_resource(ProviderList, "/providerlist")

    # Resource Request
    api.add_resource(ResourceRequestRegister, "/request")
    api.add_resource(ResourceRequest, "/request/<string:_id>")
    api.add_resource(ResourceRequestList, "/requestlist")
    api.add_resource(ResourceRequestListAll, "/requestlistall")

    # Resource
    api.add_resource(ResourceRegister, "/resource")
    api.add_resource(Resource, "/resource/<string:_id>")
    api.add_resource(ResourceList, "/resourcelist")

    # Resource Supply
    api.add_resource(ResourceSupplyRegister, "/supply")
    api.add_resource(ResourceSupply, "/supply/<string:_id>")
    api.add_resource(ResourceSupplyList, "/supplylist")

    # Shipment
    api.add_resource(ShipmentRegister, "/shipment")
    api.add_resource(Shipment, "/shipment/<string:_id>")
    api.add_resource(ShipmentList, "/shipmentlist")

    from db import mongo
    mongo.init_app(app)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=5000, debug=False)
