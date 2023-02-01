# Copyright 2023 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Test for DTensor related utilities in tf.distribute."""

from absl.testing import parameterized
import numpy as np

from tensorflow.dtensor.python import api as d_api
from tensorflow.dtensor.python import layout
from tensorflow.dtensor.python.tests import test_util
from tensorflow.python.distribute import values as values_lib
from tensorflow.python.distribute.experimental import dtensor_util
from tensorflow.python.eager import test
from tensorflow.python.framework import constant_op


class DTensorDistributedValueTest(test_util.DTensorBaseTest):

  def setUp(self):
    super().setUp()
    global_ids = test_util.create_device_ids_array((2,))
    local_ids = np.ravel(global_ids).tolist()
    mesh_dict = {
        device: layout.Mesh(['batch'], global_ids, local_ids,
                            test_util.create_device_list((2,), device))
        for device in ['TPU', 'GPU', 'CPU']
    }
    self.mesh = self.configTestMesh(mesh_dict)

    tensor_1 = constant_op.constant([1.0])
    tensor_2 = constant_op.constant([2.0])
    batch_layout = layout.Layout.batch_sharded(
        self.mesh, batch_dim='batch', rank=1)
    self.dtensor = d_api.pack([tensor_1, tensor_2], batch_layout)

  @parameterized.named_parameters([
      ('py_floats', [1.0, 2.0]),
      ('np_floats', np.array([1.0, 2.0])),
      ('tf_const', lambda: constant_op.constant([1.0, 2.0])),
      ('distribute_value', values_lib.PerReplica([1.0, 2.0])),
  ])
  def test_input_validation(self, inputs):
    if callable(inputs):
      inputs = inputs()

    with self.assertRaisesRegex(ValueError, 'can only be built with DTensor'):
      dtensor_util.DTensorDistributedValue(inputs)

  def test_unpack(self):
    v = dtensor_util.DTensorDistributedValue(self.dtensor)

    self.assertIs(self.dtensor, v.get_dtensor())

    per_replica_result = v.values
    self.assertLen(per_replica_result, 2)
    self.assertAllClose(per_replica_result[0], constant_op.constant([1.0]))
    self.assertAllClose(per_replica_result[1], constant_op.constant([2.0]))


if __name__ == '__main__':
  test.main()
