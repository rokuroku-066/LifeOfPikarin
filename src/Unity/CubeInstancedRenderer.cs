using System.Collections.Generic;
using UnityEngine;

namespace Terrarium.UnityView
{
    public sealed class CubeInstancedRenderer : MonoBehaviour
    {
        private const int MaxInstances = 1023;

        [SerializeField]
        private Mesh? _mesh;

        [SerializeField]
        private Material? _material;

        private readonly List<Matrix4x4> _matrices = new(MaxInstances);
        private readonly List<Vector4> _colors = new(MaxInstances);
        private MaterialPropertyBlock? _propertyBlock;
        private static readonly int ColorId = Shader.PropertyToID("_Color");

        public void Render(IReadOnlyList<AgentSnapshot> snapshots)
        {
            if (_mesh == null || _material == null || snapshots.Count == 0)
            {
                return;
            }

            _propertyBlock ??= new MaterialPropertyBlock();

            var index = 0;
            while (index < snapshots.Count)
            {
                var batchCount = Mathf.Min(MaxInstances, snapshots.Count - index);
                _matrices.Clear();
                _colors.Clear();

                for (var i = 0; i < batchCount; i++)
                {
                    var snapshot = snapshots[index + i];
                    var position = new Vector3(snapshot.Position.X, 0f, snapshot.Position.Y);
                    var rotation = snapshot.Velocity.LengthSquared > 1e-4f
                        ? Quaternion.LookRotation(new Vector3(snapshot.Velocity.X, 0f, snapshot.Velocity.Y))
                        : Quaternion.identity;
                    var scale = Vector3.one * snapshot.Scale;
                    _matrices.Add(Matrix4x4.TRS(position, rotation, scale));

                    var color = Color.HSVToRGB(Mathf.Repeat(snapshot.ColorHue, 1f), 1f, 1f);
                    _colors.Add(new Vector4(color.r, color.g, color.b, 1f));
                }

                _propertyBlock.Clear();
                _propertyBlock.SetVectorArray(ColorId, _colors);
                Graphics.DrawMeshInstanced(_mesh, 0, _material, _matrices, _propertyBlock);
                index += batchCount;
            }
        }
    }
}
