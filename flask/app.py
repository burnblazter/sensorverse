from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from datetime import datetime
import os
from flask_cors import CORS

# initialize the flask app
app = Flask(__name__)
CORS(app)  # enable CORS for all routes

# configure mongodb connection
app.config["MONGO_URI"] = "mongodb+srv://bhagaskara:Skr5hjuNTvpkJ0jt@glitchhunterdb.utkjx.mongodb.net/?retryWrites=true&w=majority&appName=glitchhunterdb"
# alternative: use an environment variable for better security
# app.config["MONGO_URI"] = os.environ.get("MONGO_URI", "mongodb://localhost:27017/sensorverse")

# initialize pymongo
mongo = PyMongo(app)

# optional: api key validation middleware
def validate_api_key(request):
    api_key = request.headers.get("X-API-Key")
    valid_api_key = os.environ.get("API_KEY", "sensorvers3")  # set your API key in an environment variable or hardcode for testing
    return api_key == valid_api_key

@app.route("/api/sensors", methods=["POST"])
def add_sensor_data():
    # optional: api key validation
    # if not validate_api_key(request):
    #     return jsonify({"error": "invalid API key"}), 401
    
    try:
        # get json data from request
        data = request.json
        
        # add a timestamp if it's not provided
        if "timestamp" not in data:
            data["timestamp"] = datetime.now()
        else:
            # convert timestamp to a datetime object if it's a number
            if isinstance(data["timestamp"], (int, float)):
                data["timestamp"] = datetime.fromtimestamp(data["timestamp"])
        
        # store data in mongodb
        result = mongo.db.sensor_readings.insert_one(data)
        
        return jsonify({
            "success": True,
            "message": "data stored successfully",
            "id": str(result.inserted_id)
        }), 201
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/sensors", methods=["GET"])
def get_sensor_data():
    try:
        # get optional query parameters
        device_id = request.args.get("device_id")
        limit = int(request.args.get("limit", 100))  # default to 100 records
        
        # build query
        query = {}
        if device_id:
            query["device_id"] = device_id
        
        # fetch data from mongodb
        cursor = mongo.db.sensor_readings.find(query).sort("timestamp", -1).limit(limit)
        
        # convert to list and format for json response
        results = []
        for document in cursor:
            document["_id"] = str(document["_id"])  # convert objectid to string
            results.append(document)
        
        return jsonify({
            "success": True,
            "count": len(results),
            "data": results
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/sensors/latest", methods=["GET"])
def get_latest_sensor_data():
    try:
        # get optional device_id parameter
        device_id = request.args.get("device_id")
        
        # build query
        query = {}
        if device_id:
            query["device_id"] = device_id
        
        # fetch the latest record from mongodb
        latest = mongo.db.sensor_readings.find_one(
            query, 
            sort=[("timestamp", -1)]
        )
        
        if latest:
            latest["_id"] = str(latest["_id"])  # convert objectid to string
            return jsonify({
                "success": True,
                "data": latest
            })
        else:
            return jsonify({
                "success": False,
                "message": "no data found"
            }), 404
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# simple route to check if the api is running
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "API is running"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
