import traceback

from flask_restful import Resource, reqparse
from bson import json_util
from bson.objectid import ObjectId
from flask_jwt_extended import (
    jwt_refresh_token_required,
    get_jwt_identity,
    jwt_required,
    get_raw_jwt,
)

from db import mongo

_shipment_parser = reqparse.RequestParser()
_shipment_parser.add_argument(
    "resource_name", type=str, required=True, help="This field cannot be blank."
)
_shipment_parser.add_argument(
    "resource_id", type=str, required=True, help="This field cannot be blank."
)
_shipment_parser.add_argument(
    "quantity", type=int, required=True, help="This field cannot be blank."
)
_shipment_parser.add_argument(
    "hospital_id", type=int, required=True, help="This field cannot be blank."
)
_shipment_parser.add_argument(
    "provider_id", type=int, required=True, help="This field cannot be blank."
)

_shipment_update_parser = reqparse.RequestParser()
_shipment_parser.add_argument(
    "shipped", type=bool, required=False, help="This field cannot be blank."
)
_shipment_parser.add_argument(
    "received", type=bool, required=False, help="This field cannot be blank."
)


class ShipmentRegister(Resource):
    @jwt_required
    def post(self):
        data = _shipment_parser.parse_args()

        # lookup the provider order and decrement by quantity, if zero, delete it
        try:
            supply = mongo.db.supplies.find_one(
                {"resource_id": data['resource_id'], "provider_id": data['provider_id']})
        except:
            return {"message": "There was an error looking up the resource"}, 500

        if supply.get("quantity", 0) - data.get("quantity", 0) > 0:
            try:
                mongo.db.supplies.update_one(
                    {"_id": supply.get("_id")},
                    {"$set": {"quantity": supply.get(
                        "quantity", 0) - data.get("quantity", 0)}},
                )
            except:
                return {"message": "there was an error updating the resource supply"}, 500
        else:
            try:
                mongo.db.supplies.delete_one({"_id": supply.get("_id")})
            except:
                return {"message": "An error occurred trying to delete this supply"}, 500

        # lookup the hospital order and decrement by quantity, if zero, delete it
        try:
            request = mongo.db.requests.find_one(
                {"resource_id": data['resource_id'], "hospital_id": data['hospital_id']})
        except:
            return {"message": "There was an error looking up the resource request"}, 500

        if request.get("quantity", 0) - data.get("quantity", 0) > 0:
            try:
                mongo.db.requests.update_one(
                    {"_id": request.get("_id")},
                    {"$set": {"quantity": request.get(
                        "quantity", 0) - data.get("quantity", 0)}},
                )
            except:
                return {"message": "there was an error updating the resource request"}, 500
        else:
            try:
                mongo.db.requests.delete_one({"_id": request.get("_id")})
            except:
                return {"message": "An error occurred trying to delete this request"}, 500

        # create the shipment
        try:
            mongo.db.shipments.insert_one({
                "resource_name": data["resource_name"],
                "resource_id": data['resource_id'],
                "quantity": data['quantity'],
                "provider_id": data['provider_id'],
                "hospital_id": data['hospital_id']
            })
        except:
            return {"message": "There was an error creating the shipment"}, 500

        return {"message": "shipment created"}, 201


class Shipment(Resource):

    @jwt_required
    def get(self, _id):
        try:
            shipment = mongo.db.shipments.find_one({"_id": ObjectId(_id)})
        except:
            return {"message": "An error occurred looking up the shipment"}, 500

        if shipment:
            return json_util._json_convert(shipment), 200
        return {"message": "shipment not found"}, 404

    @jwt_required
    def put(self, _id):
        data = _shipment_update_parser.parse_args()

        try:
            shipment = mongo.db.shipments.find_one(
                {"_id": shipment.get("_id")})
        except:
            return {"message": "There was an error looking up the shipment"}, 500

        if shipment:
            try:
                mongo.db.shipments.update_one(
                    {"_id": shipment.get("_id")},
                    {"$set": {
                        "shipped": shipment.get("shipped", False) or data.get("shipped", False),
                        "arrived": shipment.get("arrived", False) or data.get("arrived", False)
                    }})
            except:
                return {"message": "there was an error updating the shipment"}, 500
            return {"message": " shipment updated"}, 200

        return {"message": "this shipment does not exist"}, 404

    # Should probably not be used, since user depends on this staying forever
    @jwt_required
    def delete(self, _id):
        try:
            shipment = mongo.db.shipments.find_one({"_id": ObjectId(_id)})
        except:
            return {"message": "An error occurred trying to look up this shipment"}, 500

        if shipment:
            try:
                mongo.db.shipments.delete_one({"_id": ObjectId(_id)})
            except:
                return {"message": "An error occurred trying to delete this shipment"}, 500
            return {"message": "shipment was deleted"}, 200
        return {"message": "shipment not found"}, 404


class ShipmentList(Resource):
    @jwt_required
    def get(self):
        try:
            user = mongo.db.users.find_one(
                {"_id": ObjectId(get_jwt_identity())})
        except:
            return {"message": "There was an error looking up the user"}, 500

        if user.get('provider_id'):
            try:
                provider = mongo.db.providers.find_one(
                    {"_id": ObjectId(user['provider_id'])})
            except:
                return {"message": "There was an error looking up the provider"}, 500

            try:
                shipments = mongo.db.shipments.find({
                    "provider_id": str(provider['_id'])
                })
            except:
                return {"message": "There was an error looking up the resource supply"}, 500
        else:
            try:
                hospital = mongo.db.hospitals.find_one(
                    {"_id": ObjectId(user['hospital_id'])})
            except:
                return {"message": "There was an error looking up the hospital"}, 500

            try:
                shipments = mongo.db.shipments.find({
                    "hospital_id": str(hospital['_id'])
                })
            except:
                return {"message": "There was an error looking up the resource request"}, 500

        return {"supplies": json_util._json_convert(shipments)}, 200
