"""RL-Games actor-critic network for RGB Franka multi-object PPO."""

from __future__ import annotations

import torch
import torch.nn as nn
import torchvision
from rl_games.algos_torch.running_mean_std import RunningMeanStd


def _activation(name: str | None) -> nn.Module:
    if name in (None, "None"):
        return nn.Identity()
    if name == "elu":
        return nn.ELU()
    if name == "relu":
        return nn.ReLU()
    if name == "gelu":
        return nn.GELU()
    if name == "swish":
        return nn.SiLU()
    if name == "tanh":
        return nn.Tanh()
    if name == "sigmoid":
        return nn.Sigmoid()
    raise ValueError(f"Unsupported activation: {name!r}")


def _group_norm(num_channels: int) -> nn.GroupNorm:
    return nn.GroupNorm(num_groups=min(32, num_channels), num_channels=num_channels)


class RgbResnetEncoder(nn.Module):
    """ResNet18 RGB encoder matching the DEXTRAH distillation RGB path."""

    def __init__(
        self,
        out_features: int,
        *,
        pretrained: bool = True,
        use_group_norm: bool = False,
        train_backbone: bool = False,
        encoder_batch_size: int = 64,
        backbone_dtype: str = "bfloat16",
        clamp_input: bool = False,
    ):
        super().__init__()
        if pretrained and use_group_norm:
            raise ValueError("ImageNet ResNet18 weights require the standard BatchNorm ResNet layout")
        self.train_backbone = bool(train_backbone)
        self.encoder_batch_size = int(encoder_batch_size)
        if backbone_dtype == "bfloat16":
            self.backbone_dtype = torch.bfloat16
        elif backbone_dtype == "float16":
            self.backbone_dtype = torch.float16
        elif backbone_dtype == "float32":
            self.backbone_dtype = torch.float32
        else:
            raise ValueError(f"Unsupported RGB backbone dtype: {backbone_dtype!r}")
        self.clamp_input = bool(clamp_input)
        norm_layer = _group_norm if use_group_norm else None
        weights = torchvision.models.ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
        if norm_layer is None:
            self.backbone = torchvision.models.resnet18(weights=weights)
        else:
            self.backbone = torchvision.models.resnet18(weights=weights, norm_layer=norm_layer)
        self.backbone.fc = nn.Identity()
        self.backbone.to(dtype=self.backbone_dtype)
        if not self.train_backbone:
            self.backbone.eval()
            for param in self.backbone.parameters():
                param.requires_grad_(False)
        self.proj = nn.Linear(512, out_features)
        self.register_buffer("mean", torch.tensor((0.485, 0.456, 0.406)).view(1, 3, 1, 1), persistent=False)
        self.register_buffer("std", torch.tensor((0.229, 0.224, 0.225)).view(1, 3, 1, 1), persistent=False)

    def train(self, mode: bool = True):
        super().train(mode)
        if not self.train_backbone:
            self.backbone.eval()
        return self

    def _forward_backbone(self, rgb: torch.Tensor) -> torch.Tensor:
        batch_size = int(self.encoder_batch_size)
        if batch_size <= 0 or rgb.shape[0] <= batch_size:
            return self.backbone(rgb)
        return torch.cat([self.backbone(chunk) for chunk in rgb.split(batch_size, dim=0)], dim=0)

    def forward(self, rgb: torch.Tensor) -> torch.Tensor:
        rgb = rgb.to(dtype=torch.float32)
        if self.clamp_input:
            rgb = torch.clamp(rgb, 0.0, 1.0)
        rgb = (rgb - self.mean) / self.std
        rgb = rgb.to(dtype=self.backbone_dtype)
        if self.train_backbone:
            resnet_out = self._forward_backbone(rgb)
        else:
            with torch.no_grad():
                resnet_out = self._forward_backbone(rgb)
        return self.proj(resnet_out.to(dtype=torch.float32))


class A2CRgbResnetBuilder:
    """Minimal RL-Games network builder for continuous A2C/PPO."""

    def load(self, params: dict):
        self.params = params

    def build(self, name: str, **kwargs):
        return self.Network(self.params, **kwargs)

    def __call__(self, name: str, **kwargs):
        return self.build(name, **kwargs)

    class Network(nn.Module):
        def __init__(self, params: dict, **kwargs):
            super().__init__()
            actions_num = int(kwargs.pop("actions_num"))
            input_shape = kwargs.pop("input_shape")
            self.value_size = int(kwargs.pop("value_size", 1))
            self.num_seqs = int(kwargs.pop("num_seqs", 1))
            self.central_value = bool(params.get("central_value", False))

            if len(input_shape) != 1:
                raise ValueError(f"RGB ResNet PPO expects a flat observation vector, got input_shape={input_shape}")
            rgb_cfg = params.get("rgb", {})
            self.proprio_dim = int(rgb_cfg.get("robot_proprio_dim", 33))
            self.image_channels = int(rgb_cfg.get("image_channels", 3))
            self.image_height = int(rgb_cfg.get("image_height", 240))
            self.image_width = int(rgb_cfg.get("image_width", 320))
            self.image_flat_dim = self.image_channels * self.image_height * self.image_width
            expected_obs_dim = self.proprio_dim + self.image_flat_dim
            if int(input_shape[0]) != expected_obs_dim:
                raise ValueError(
                    "RGB ResNet PPO observation mismatch: "
                    f"input_shape={input_shape[0]} expected={expected_obs_dim} "
                    f"(proprio={self.proprio_dim}, image={self.image_channels}x{self.image_height}x{self.image_width})"
                )

            visual_features = int(rgb_cfg.get("visual_features", 32))
            pretrained = bool(rgb_cfg.get("pretrained", True))
            use_group_norm = bool(rgb_cfg.get("use_group_norm", False))
            train_backbone = bool(rgb_cfg.get("train_backbone", False))
            encoder_batch_size = int(rgb_cfg.get("encoder_batch_size", 64))
            backbone_dtype = str(rgb_cfg.get("backbone_dtype", "bfloat16"))
            self.running_mean_img = bool(rgb_cfg.get("running_mean_img", True))
            self.encoder = RgbResnetEncoder(
                visual_features,
                pretrained=pretrained,
                use_group_norm=use_group_norm,
                train_backbone=train_backbone,
                encoder_batch_size=encoder_batch_size,
                backbone_dtype=backbone_dtype,
                clamp_input=bool(rgb_cfg.get("clamp_input", False)),
            )
            if self.running_mean_img:
                self.image_running_mean_std = RunningMeanStd(
                    (self.image_channels, self.image_height, self.image_width)
                )
            else:
                self.image_running_mean_std = nn.Identity()

            mlp_cfg = params["mlp"]
            activation = str(mlp_cfg.get("activation", "elu"))
            units = [int(v) for v in mlp_cfg.get("units", [512, 256, 128])]
            layers: list[nn.Module] = []
            in_size = self.proprio_dim + visual_features
            for unit in units:
                layers.append(nn.Linear(in_size, unit))
                layers.append(_activation(activation))
                in_size = unit
            self.trunk = nn.Sequential(*layers)
            self.mu = nn.Linear(in_size, actions_num)
            self.value = nn.Linear(in_size, self.value_size)

            space_cfg = params.get("space", {}).get("continuous", {})
            self.mu_act = _activation(space_cfg.get("mu_activation"))
            self.sigma_act = _activation(space_cfg.get("sigma_activation"))
            self.fixed_sigma = bool(space_cfg.get("fixed_sigma", True))
            sigma_val = float(space_cfg.get("sigma_init", {}).get("val", 0.0))
            if self.fixed_sigma:
                self.sigma = nn.Parameter(torch.full((actions_num,), sigma_val, dtype=torch.float32))
            else:
                self.sigma = nn.Linear(in_size, actions_num)
                nn.init.constant_(self.sigma.bias, sigma_val)

        def _split_obs(self, obs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            obs = obs.to(dtype=torch.float32)
            proprio = obs[:, : self.proprio_dim]
            rgb_flat = obs[:, self.proprio_dim : self.proprio_dim + self.image_flat_dim]
            rgb = rgb_flat.reshape(obs.shape[0], self.image_channels, self.image_height, self.image_width)
            return proprio, rgb

        def forward(self, obs_dict: dict):
            obs = obs_dict["obs"]
            proprio, rgb = self._split_obs(obs)
            rgb = self.image_running_mean_std(rgb)
            visual = self.encoder(rgb)
            out = self.trunk(torch.cat((proprio, visual), dim=-1))
            value = self.value(out)
            states = obs_dict.get("rnn_states", None)

            if self.central_value:
                return value, states

            mu = self.mu_act(self.mu(out))
            if self.fixed_sigma:
                sigma = self.sigma_act(self.sigma).expand_as(mu)
            else:
                sigma = self.sigma_act(self.sigma(out))
            return mu, sigma, value, states

        def is_separate_critic(self) -> bool:
            return False

        def is_rnn(self) -> bool:
            return False

        def get_default_rnn_state(self):
            return None

        def get_value_layer(self):
            return self.value

        def get_aux_loss(self) -> dict[str, torch.Tensor]:
            return {}
