import pytest
import json
import numpy as np
from google.protobuf import json_format
import base64

from seldon_core.combiner_microservice import get_rest_microservice, SeldonCombinerGRPC, get_grpc_server
from seldon_core.proto import prediction_pb2


class UserObject(object):
    def __init__(self, metrics_ok=True, ret_nparray=False):
        self.metrics_ok = metrics_ok
        self.ret_nparray = ret_nparray
        self.nparray = np.array([1, 2, 3])

    def aggregate(self, Xs, features_names):
        if self.ret_nparray:
            return self.nparray
        else:
            print("Aggregate input called - will return first item")
            print(Xs)
            return Xs[0]
        
    def tags(self):
        return {"mytag": 1}

    def metrics(self):
        if self.metrics_ok:
            return [{"type": "COUNTER", "key": "mycounter", "value": 1}]
        else:
            return [{"type": "BAD", "key": "mycounter", "value": 1}]

class UserObjectLowLevel(object):
    def __init__(self, metrics_ok=True, ret_nparray=False):
        self.metrics_ok = metrics_ok
        self.ret_nparray = ret_nparray
        self.nparray = np.array([1, 2, 3])

    def aggregate_rest(self, Xs):
        return {"data":{"ndarray":[9,9]}}

    def aggregate_grpc(self, X):
        arr = np.array([9, 9])
        datadef = prediction_pb2.DefaultData(
            tensor=prediction_pb2.Tensor(
                shape=(2, 1),
                values=arr
            )
        )
        request = prediction_pb2.SeldonMessage(data=datadef)
        return request


def test_aggreate_ok():
    user_object = UserObject()
    app = get_rest_microservice(user_object, debug=True)
    client = app.test_client()
    rv = client.get('/aggregate?json={"seldonMessages":[{"data":{"ndarray":[1]}}]}')
    print(rv)
    j = json.loads(rv.data)
    print(j)
    assert rv.status_code == 200
    assert j["meta"]["tags"] == {"mytag": 1}
    assert j["meta"]["metrics"] == user_object.metrics()
    assert j["data"]["ndarray"] == [1]

def test_aggreate_invalid_message():
    user_object = UserObject()
    app = get_rest_microservice(user_object, debug=True)
    client = app.test_client()
    rv = client.get('/aggregate?json={"wrong":[{"data":{"ndarray":[1]}}]}')
    assert rv.status_code == 400
    j = json.loads(rv.data)
    print(j)
    assert j["status"]["reason"] == "MICROSERVICE_BAD_DATA"
    assert j["status"]["info"] == "Request must contain seldonMessages field"

def test_aggreate_no_list():
    user_object = UserObject()
    app = get_rest_microservice(user_object, debug=True)
    client = app.test_client()
    rv = client.get('/aggregate?json={"seldonMessages":{"data":{"ndarray":[1]}}}')
    assert rv.status_code == 400
    j = json.loads(rv.data)
    print(j)
    assert j["status"]["reason"] == "MICROSERVICE_BAD_DATA"
    assert j["status"]["info"] == "seldonMessages field is not a list"

def test_aggreate_empty_list():
    user_object = UserObject()
    app = get_rest_microservice(user_object, debug=True)
    client = app.test_client()
    rv = client.get('/aggregate?json={"seldonMessages":[]}')
    assert rv.status_code == 400
    j = json.loads(rv.data)
    print(j)
    assert j["status"]["reason"] == "MICROSERVICE_BAD_DATA"
    assert j["status"]["info"] == "seldonMessages field is empty"
    

def test_aggreate_bad_messages():
    user_object = UserObject()
    app = get_rest_microservice(user_object, debug=True)
    client = app.test_client()
    rv = client.get('/aggregate?json={"seldonMessages":[{"data2":{"ndarray":[1]}}]}')
    assert rv.status_code == 400
    j = json.loads(rv.data)
    print(j)
    assert j["status"]["reason"] == "MICROSERVICE_BAD_DATA"
    assert j["status"]["info"] == "Invalid SeldonMessage at index 0 : Request must contain Default Data or binData or strData"


def test_aggreate_ok_2messages():
    user_object = UserObject()
    app = get_rest_microservice(user_object, debug=True)
    client = app.test_client()
    rv = client.get('/aggregate?json={"seldonMessages":[{"data":{"ndarray":[1]}},{"data":{"ndarray":[2]}}]}')
    print(rv)
    j = json.loads(rv.data)
    print(j)
    assert rv.status_code == 200
    assert j["meta"]["tags"] == {"mytag": 1}
    assert j["meta"]["metrics"] == user_object.metrics()
    assert j["data"]["ndarray"] == [1]
    
def test_aggreate_ok_bindata():
    user_object = UserObject()
    app = get_rest_microservice(user_object, debug=True)
    client = app.test_client()
    rv = client.get('/aggregate?json={"seldonMessages":[{"binData":"123"},{"binData":"456"}]}')
    print(rv)
    j = json.loads(rv.data)
    print(j)
    assert rv.status_code == 200
    assert j["meta"]["tags"] == {"mytag": 1}
    assert j["meta"]["metrics"] == user_object.metrics()
    assert j["binData"] == "123"
    
def test_aggregate_bad_metrics():
    user_object = UserObject(metrics_ok=False)
    app = get_rest_microservice(user_object, debug=True)
    client = app.test_client()
    rv = client.get('/aggregate?json={"seldonMessages":[{"data":{"ndarray":[1]}},{"data":{"ndarray":[2]}}]}')
    j = json.loads(rv.data)
    print(j)
    assert rv.status_code == 400


def test_aggreate_ok_lowlevel():
    user_object = UserObjectLowLevel()
    app = get_rest_microservice(user_object, debug=True)
    client = app.test_client()
    rv = client.get('/aggregate?json={"seldonMessages":[{"data":{"ndarray":[1]}},{"data":{"ndarray":[2]}}]}')
    print(rv)
    j = json.loads(rv.data)
    print(j)
    assert rv.status_code == 200
    assert j["data"]["ndarray"] == [9, 9]


def test_aggregate_proto_ok():
    user_object = UserObject()
    app = SeldonCombinerGRPC(user_object)
    arr1 = np.array([1, 2])
    datadef1 = prediction_pb2.DefaultData(
        tensor=prediction_pb2.Tensor(
            shape=(2, 1),
            values=arr1
        )
    )
    arr2 = np.array([3, 4])
    datadef2 = prediction_pb2.DefaultData(
        tensor=prediction_pb2.Tensor(
            shape=(2, 1),
            values=arr2
        )
    )
    msg1 = prediction_pb2.SeldonMessage(data=datadef1)
    msg2 = prediction_pb2.SeldonMessage(data=datadef2)
    request = prediction_pb2.SeldonMessageList(seldonMessages=[msg1,msg2])
    resp = app.Aggregate(request, None)
    jStr = json_format.MessageToJson(resp)
    j = json.loads(jStr)
    print(j)
    assert j["meta"]["tags"] == {"mytag": 1}
    # add default type
    j["meta"]["metrics"][0]["type"] = "COUNTER"
    assert j["meta"]["metrics"] == user_object.metrics()
    assert j["data"]["tensor"]["shape"] == [2, 1]
    assert j["data"]["tensor"]["values"] == [1, 2]
    

def test_aggregate_proto_bin_data():
    user_object = UserObject()
    app = SeldonCombinerGRPC(user_object)
    binData = b"\0\1"
    msg1 = prediction_pb2.SeldonMessage(binData=binData)
    request = prediction_pb2.SeldonMessageList(seldonMessages=[msg1])
    resp = app.Aggregate(request, None)
    assert resp.binData == binData

def test_aggregate_proto_lowlevel_ok():
    user_object = UserObjectLowLevel()
    app = SeldonCombinerGRPC(user_object)
    arr1 = np.array([1, 2])
    datadef1 = prediction_pb2.DefaultData(
        tensor=prediction_pb2.Tensor(
            shape=(2, 1),
            values=arr1
        )
    )
    arr2 = np.array([3, 4])
    datadef2 = prediction_pb2.DefaultData(
        tensor=prediction_pb2.Tensor(
            shape=(2, 1),
            values=arr2
        )
    )
    msg1 = prediction_pb2.SeldonMessage(data=datadef1)
    msg2 = prediction_pb2.SeldonMessage(data=datadef2)
    request = prediction_pb2.SeldonMessageList(seldonMessages=[msg1,msg2])
    resp = app.Aggregate(request, None)
    jStr = json_format.MessageToJson(resp)
    j = json.loads(jStr)
    print(j)
    assert j["data"]["tensor"]["shape"] == [2, 1]
    assert j["data"]["tensor"]["values"] == [9, 9]
    

def test_get_grpc_server():
    user_object = UserObject(ret_nparray=True)
    server = get_grpc_server(user_object)
    
