import timesfm
import numpy as np
import pandas as pd

tfm = timesfm.TimesFM_2p5_200M_torch.from_pretrained("google/timesfm-2.5-200m-pytorch")
inputs = [np.sin(np.linspace(0, 10, 100)).tolist()]

# Test dynamic covariates
dynamic_num = {
    "tnx": [np.cos(np.linspace(0, 12, 120)).tolist()] # 100 input + 20 horizon
}

try:
    print("Forecasting with covariates...")
    res = tfm.forecast_with_covariates(
        inputs=inputs,
        dynamic_numerical_covariates=dynamic_num
    )
    print("Success! Res length:", len(res))
    if isinstance(res, tuple):
        print("Res shape:", res[0].shape)
    else:
        print("Res:", type(res))
except Exception as e:
    import traceback
    traceback.print_exc()
