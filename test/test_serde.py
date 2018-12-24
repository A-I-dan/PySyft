from syft.serde import _simplify
from syft.serde import serialize
from syft.serde import deserialize
from syft.serde import _compress
from syft.serde import _decompress

from syft import TorchHook
from syft.frameworks.torch.tensors import PointerTensor
import torch
import syft
from torch import Tensor
import numpy
import msgpack
import pytest


def test_tuple_simplify():
    input = ("hello", "world")
    target = [1, ("hello", "world")]
    assert _simplify(input) == target


def test_list_simplify():
    input = ["hello", "world"]
    target = [2, ["hello", "world"]]
    assert _simplify(input) == target


def test_set_simplify():
    input = set(["hello", "world"])
    target = [3, ["hello", "world"]]
    assert _simplify(input)[0] == target[0]
    assert set(_simplify(input)[1]) == set(target[1])


def test_float_simplify():
    input = 5.6
    target = 5.6
    assert _simplify(input) == target


def test_int_simplify():
    input = 5
    target = 5
    assert _simplify(input) == target


def test_string_simplify():
    input = "hello"
    target = "hello"
    assert _simplify(input) == target


def test_dict_simplify():
    input = {"hello": "world"}
    target = [4, {"hello": "world"}]
    assert _simplify(input) == target


def test_range_simplify():
    input = range(1, 3, 4)
    target = [5, (1, 3, 4)]
    assert _simplify(input) == target


def test_torch_tensor_simplify():
    input = Tensor(numpy.random.random((100, 100)))
    output = _simplify(input)
    assert type(output) == list
    assert type(output[1]) == bytes


def test_ndarray_simplify():
    input = numpy.random.random((100, 100))
    output = _simplify(input)
    assert type(output[1][0]) == bytes
    assert output[1][1] == input.shape
    assert output[1][2] == input.dtype.name


def test_ellipsis_simplify():
    assert _simplify(Ellipsis)[1] == b""


def test_pointer_tensor_simplify():
    alice = syft.VirtualWorker(id="alice")
    input = PointerTensor(id=1000, location=alice, owner=alice)
    output = _simplify(input)
    assert output[1]["id"] == input.id
    assert output[1]["owner"] == input.owner.id
    assert output[1]["location"] == input.location.id
    assert output[1]["id_at_location"] == input.id_at_location


@pytest.mark.parametrize("compress", [True, False])
def test_torch_Tensor_serde(compress):

    t = Tensor(numpy.random.random((100, 100)))
    t_serialized = serialize(t, compress=compress)
    t_serialized_deserialized = deserialize(t_serialized, compressed=compress)
    assert (t == t_serialized_deserialized).all()


@pytest.mark.parametrize("compress", [True, False])
def test_tuple_serde(compress):

    # Test with a simple datatype
    tuple = (1, 2)
    tuple_serialized = serialize(tuple, compress=compress)
    tuple_serialized_deserialized = deserialize(tuple_serialized, compressed=compress)
    assert tuple == tuple_serialized_deserialized

    # Test with a complex data structure
    tensor_one = Tensor(numpy.random.random((100, 100)))
    tensor_two = Tensor(numpy.random.random((100, 100)))
    tuple = (tensor_one, tensor_two)
    tuple_serialized = serialize(tuple, compress=compress)
    tuple_serialized_deserialized = deserialize(tuple_serialized, compressed=compress)
    # `assert tuple_serialized_deserialized == tuple` does not work, therefore it's split
    # into 3 assertions
    assert type(tuple_serialized_deserialized) == type(tuple)
    assert (tuple_serialized_deserialized[0] == tensor_one).all()
    assert (tuple_serialized_deserialized[1] == tensor_two).all()


@pytest.mark.parametrize("compress", [True, False])
def test_bytearray_serde(compress):
    bytearr = bytearray("This is a teststring", "utf-8")
    bytearr_serialized = serialize(bytearr, compress=compress)
    bytearr_serialized_desirialized = deserialize(bytearr_serialized, compressed=compress)
    assert bytearr == bytearr_serialized_desirialized

    bytearr = bytearray(numpy.random.random((100, 100)))
    bytearr_serialized = serialize(bytearr, compress=False)
    bytearr_serialized_desirialized = deserialize(bytearr_serialized, compressed=False)
    assert bytearr == bytearr_serialized_desirialized


@pytest.mark.parametrize("compress", [True, False])
def test_ndarray_serde(compress):
    arr = numpy.random.random((100, 100))
    arr_serialized = serialize(arr, compress=compress)

    arr_serialized_deserialized = deserialize(arr_serialized, compressed=compress)

    assert numpy.array_equal(arr, arr_serialized_deserialized)


@pytest.mark.parametrize("compressScheme", ["lz4", "zstd"])
def test_compress_decompress(compressScheme):
    original = msgpack.dumps([1, 2, 3])
    compressed = _compress(original, compressScheme=compressScheme)
    decompressed = _decompress(compressed, compressScheme=compressScheme)
    assert type(compressed) == bytes
    assert original == decompressed


@pytest.mark.parametrize("compressScheme", ["lz4", "zstd"])
def test_compressed_serde(compressScheme):
    arr = numpy.random.random((100, 100))
    arr_serialized = serialize(arr, compress=True, compressScheme=compressScheme)

    arr_serialized_deserialized = deserialize(
        arr_serialized, compressed=True, compressScheme=compressScheme
    )
    assert numpy.array_equal(arr, arr_serialized_deserialized)


@pytest.mark.parametrize("compress", [True, False])
def test_dict_serde(compress):

    # Test with integers
    _dict = {1: 1, 2: 2, 3: 3}
    dict_serialized = serialize(_dict, compress=compress)
    dict_serialized_deserialized = deserialize(dict_serialized, compressed=compress)
    assert _dict == dict_serialized_deserialized

    # Test with strings
    _dict = {"one": 1, "two": 2, "three": 3}
    dict_serialized = serialize(_dict, compress=compress)
    dict_serialized_deserialized = deserialize(dict_serialized, compressed=compress)
    assert _dict == dict_serialized_deserialized

    # Test with a complex data structure
    tensor_one = Tensor(numpy.random.random((100, 100)))
    tensor_two = Tensor(numpy.random.random((100, 100)))
    _dict = {0: tensor_one, 1: tensor_two}
    dict_serialized = serialize(_dict, compress=compress)
    dict_serialized_deserialized = deserialize(dict_serialized, compressed=compress)
    # `assert dict_serialized_deserialized == _dict` does not work, therefore it's split
    # into 3 assertions
    assert type(dict_serialized_deserialized) == type(_dict)
    assert (dict_serialized_deserialized[0] == tensor_one).all()
    assert (dict_serialized_deserialized[1] == tensor_two).all()


@pytest.mark.parametrize("compress", [True, False])
def test_range_serde(compress):
    _range = range(1, 2, 3)

    range_serialized = serialize(_range, compress=compress)

    range_serialized_deserialized = deserialize(range_serialized, compressed=compress)

    assert _range == range_serialized_deserialized


@pytest.mark.parametrize("compress", [True, False])
def test_list_serde(compress):

    # Test with integers
    _list = [1, 2]
    list_serialized = serialize(_list, compress=compress)
    list_serialized_deserialized = deserialize(list_serialized, compressed=compress)
    assert _list == list_serialized_deserialized

    # Test with strings
    _list = ["hello", "world"]
    list_serialized = serialize(_list, compress=compress)
    list_serialized_deserialized = deserialize(list_serialized, compressed=compress)
    assert _list == list_serialized_deserialized

    # Test with a complex data structure
    tensor_one = Tensor(numpy.random.random((100, 100)))
    tensor_two = Tensor(numpy.random.random((100, 100)))
    _list = (tensor_one, tensor_two)
    list_serialized = serialize(_list, compress=compress)
    list_serialized_deserialized = deserialize(list_serialized, compressed=compress)
    # `assert list_serialized_deserialized == _list` does not work, therefore it's split
    # into 3 assertions
    assert type(list_serialized_deserialized) == type(_list)
    assert (list_serialized_deserialized[0] == tensor_one).all()
    assert (list_serialized_deserialized[1] == tensor_two).all()


@pytest.mark.parametrize("compress", [True, False])
def test_set_serde(compress):

    # Test with integers
    _set = set([1, 2])
    set_serialized = serialize(_set, compress=compress)
    set_serialized_deserialized = deserialize(set_serialized, compressed=compress)
    assert _set == set_serialized_deserialized

    # Test with strings
    _set = set(["hello", "world"])
    set_serialized = serialize(_set, compress=compress)
    set_serialized_deserialized = deserialize(set_serialized, compressed=compress)
    assert _set == set_serialized_deserialized

    # Test with a complex data structure
    tensor_one = Tensor(numpy.random.random((100, 100)))
    tensor_two = Tensor(numpy.random.random((100, 100)))
    _set = (tensor_one, tensor_two)
    set_serialized = serialize(_set, compress=compress)
    set_serialized_deserialized = deserialize(set_serialized, compressed=compress)
    # `assert set_serialized_deserialized == _set` does not work, therefore it's split
    # into 3 assertions
    assert type(set_serialized_deserialized) == type(_set)
    assert (set_serialized_deserialized[0] == tensor_one).all()
    assert (set_serialized_deserialized[1] == tensor_two).all()


@pytest.mark.parametrize("compress", [True, False])
def test_slice_serde(compress):
    s = slice(0, 100, 2)
    x = numpy.random.rand(100)
    s_serialized = serialize(s, compress=compress)
    s_serialized_deserialized = deserialize(s_serialized, compressed=compress)

    assert type(s) == type(s_serialized_deserialized)
    assert (x[s] == x[s_serialized_deserialized]).all()

    s = slice(40, 50)
    x = numpy.random.rand(100)
    s_serialized = serialize(s, compress=False)
    s_serialized_deserialized = deserialize(s_serialized, compressed=False)

    assert type(s) == type(s_serialized_deserialized)
    assert (x[s] == x[s_serialized_deserialized]).all()


@pytest.mark.parametrize("compress", [True, False])
def test_float_serde(compress):
    x = 0.5
    y = 1.5

    x_serialized = serialize(x, compress=compress)
    x_serialized_deserialized = deserialize(x_serialized, compressed=compress)

    y_serialized = serialize(y, compress=compress)
    y_serialized_deserialized = deserialize(y_serialized, compressed=compress)

    assert x_serialized_deserialized == x
    assert y_serialized_deserialized == y


def test_compressed_float():
    x = 0.5
    y = 1.5

    x_serialized = serialize(x, compress=True)
    x_serialized_deserialized = deserialize(x_serialized, compressed=True)

    y_serialized = serialize(y, compress=True)
    y_serialized_deserialized = deserialize(y_serialized, compressed=True)

    assert x_serialized_deserialized == x
    assert y_serialized_deserialized == y


@pytest.mark.parametrize(
    "compress, compressScheme", [(True, "lz4"), (False, "lz4"), (True, "zstd"), (False, "zstd")]
)
def test_hooked_tensor(compress, compressScheme):

    t = Tensor(numpy.random.random((100, 100)))
    t_serialized = serialize(t, compress=compress, compressScheme=compressScheme)
    t_serialized_deserialized = deserialize(
        t_serialized, compressed=compress, compressScheme=compressScheme
    )
    assert (t == t_serialized_deserialized).all()


def test_PointerTensor(workers):
    t = PointerTensor(id=1000, location=workers["alice"], owner=workers["alice"])
    t_serialized = serialize(t, compress=False)
    t_serialized_deserialized = deserialize(t_serialized, compressed=False)

    assert t.id == t_serialized_deserialized.id
    assert t.location.id == t_serialized_deserialized.location
    assert t.owner.id == t_serialized_deserialized.owner
    assert t.id_at_location == t_serialized_deserialized.id_at_location
