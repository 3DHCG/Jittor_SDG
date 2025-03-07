from inspect import isfunction
from math import log, pi
import jittor as jt
from jittor import nn
from jittor import einops 


# helper functions


def exists(val):
    return val is not None


def broadcat(tensors, dim=-1):
    num_tensors = len(tensors)
    shape_lens = set(list(map(lambda t: len(t.shape), tensors)))
    assert len(shape_lens) == 1, "tensors must all have the same number of dimensions"
    shape_len = list(shape_lens)[0]

    dim = (dim + shape_len) if dim < 0 else dim
    dims = list(zip(*map(lambda t: list(t.shape), tensors)))

    expandable_dims = [(i, val) for i, val in enumerate(dims) if i != dim]
    assert all(
        [*map(lambda t: len(set(t[1])) <= 2, expandable_dims)]
    ), "invalid dimensions for broadcastable concatentation"
    max_dims = list(map(lambda t: (t[0], max(t[1])), expandable_dims))
    expanded_dims = list(map(lambda t: (t[0], (t[1],) * num_tensors), max_dims))
    expanded_dims.insert(dim, (dim, dims[dim]))
    expandable_shapes = list(zip(*map(lambda t: t[1], expanded_dims)))
    tensors = list(map(lambda t: t[0].expand(*t[1]), zip(tensors, expandable_shapes)))
    return jt.concat(tensors, dim=dim)

# rotary embedding helper functions

def rotate_half(x):
    x = einops.rearrange(x, "... (d r) -> ... d r", r=2)
    x1, x2 = jt.unbind(x,dim=-1)

    x = jt.stack([-x2, x1], dim=-1)
    return einops.rearrange(x, "... d r -> ... (d r)")

def apply_rotary_emb(freqs, t, start_index=0):
    freqs = freqs.astype(t.dtype)
    rot_dim = freqs.shape[-1]
    end_index = start_index + rot_dim
    assert (
        rot_dim <= t.shape[-1]
    ), f"feature dimension {t.shape[-1]} is not of sufficient size to rotate in all the positions {rot_dim}"
    t_left, t, t_right = (
        t[..., :start_index],
        t[..., start_index:end_index],
        t[..., end_index:],
    )
    t = (t * jt.cos(freqs)) + (rotate_half(t) * jt.sin(freqs))
    return jt.concat((t_left, t, t_right), dim=-1)
# learned rotation helpers

def apply_learned_rotations(rotations, t, start_index=0, freq_ranges=None):
    if exists(freq_ranges):
        rotations = jt.linalg.einsum("..., f -> ... f", rotations, freq_ranges)
        rotations = einops.rearrange(rotations, "... r f -> ... (r f)")

    rotations = einops.repeat(rotations, "... n -> ... (n r)", r=2)
    return apply_rotary_emb(rotations, t, start_index=start_index)


class RotaryEmbedding(nn.Module):
    def __init__(
        self,
        dim,
        custom_freqs=None,
        freqs_for="lang",
        theta=10000,
        max_freq=10,
        
        num_freqs=1,
        learned_freq=False,
    ):
        super().__init__()
        if exists(custom_freqs):
            freqs = custom_freqs
        elif freqs_for == "lang":
            freqs = 1.0 / (
                theta ** (jt.arange(0, dim, 2)[: (dim // 2)].float() / dim)
            )
        elif freqs_for == "pixel":
            freqs = jt.linspace(1.0, max_freq / 2, dim // 2) *pi
        elif freqs_for == "constant":
            freqs = jt.ones(num_freqs).float()
        else:
            raise ValueError(f"unknown modality {freqs_for}")


        self.cache = dict()

        if learned_freq:
            self.freqs = jt.array(freqs)
            self.freqs.requires_grad=True
        else:
            self.freqs = jt.array(freqs)
            self.freqs.requires_grad=False

    def rotate_queries_or_keys(self, t, seq_dim=-2):
        seq_len = t.shape[seq_dim]
        freqs = self.execute(
            lambda: jt.arange(seq_len), cache_key=seq_len
        )
        return apply_rotary_emb(freqs, t)


    def execute(self, t, cache_key=None):
        if exists(cache_key) and cache_key in self.cache:
            return self.cache[cache_key]

        if isfunction(t):
            t = t()

        freqs = self.freqs
        freqs = jt.linalg.einsum("..., f -> ... f", jt.type_as(t,freqs), freqs)
        freqs = einops.repeat(freqs, "... n -> ... (n r)", r=2)
        
        if exists(cache_key):
            self.cache[cache_key] = freqs

        return freqs