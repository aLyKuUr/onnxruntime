// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

#pragma once

#include "core/common/common.h"
#include "core/framework/op_kernel.h"
#include "core/providers/cpu/tensor/split.h"

namespace onnxruntime {

class SequenceLength final : public OpKernel {
 public:
  SequenceLength(const OpKernelInfo& info) : OpKernel(info) {
  }

  Status Compute(OpKernelContext* context) const override;
};

class SequenceAt final : public OpKernel {
 public:
  SequenceAt(const OpKernelInfo& info) : OpKernel(info) {
  }

  Status Compute(OpKernelContext* context) const override;
};

class SequenceEmpty final : public OpKernel {
 public:
  SequenceEmpty(const OpKernelInfo& info);
  Status Compute(OpKernelContext* context) const override;

 private:
  int64_t dtype_{};
};

class SequenceInsert final : public OpKernel {
 public:
  SequenceInsert(const OpKernelInfo& info) : OpKernel(info) {
  }
  Status Compute(OpKernelContext* context) const override;
};

class SequenceErase final : public OpKernel {
 public:
  SequenceErase(const OpKernelInfo& info) : OpKernel(info) {
  }
  Status Compute(OpKernelContext* context) const override;
};

class SequenceConstruct final : public OpKernel {
 public:
  SequenceConstruct(const OpKernelInfo& info) : OpKernel(info) {
  }
  Status Compute(OpKernelContext* context) const override;
};

class SplitToSequence final : public OpKernel {
 public:
  SplitToSequence(const OpKernelInfo& info);
  Status Compute(OpKernelContext* context) const override;

 private:
  template <typename T>
  Status ComputeImpl(OpKernelContext& context, const Tensor& input) const;
  Status PrepareForCompute(const TensorShape& input_shape, int& num_outputs, int64_t& axis, int& before_dims,
                           int& after_dims_including_split_axis, int& after_dims_excluding_split,
                           int64_t split_scalar;
                           std::vector<int64_t> & split_sizes) const;
  int64_t axis_{};
  int64_t keepdims{1};
};
}  //namespace onnxruntime
