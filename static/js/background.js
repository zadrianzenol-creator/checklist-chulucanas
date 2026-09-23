(() => {
  const canvas = document.getElementById("bg3d");
  if (!canvas) return;

  const isMobile = window.innerWidth < 768;
  const COUNT = isMobile ? 420 : 1400;

  import("https://unpkg.com/three@0.160.0/build/three.module.js").then((THREE) => {
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x05070f, 0.045);

    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 120);
    camera.position.z = 9;

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    const colors = [0x6366f1, 0x8b5cf6, 0x22d3ee, 0x818cf8];

    // Puntos flotantes
    const positions = new Float32Array(COUNT * 3);
    const colArr = new Float32Array(COUNT * 3);
    const tempColor = new THREE.Color();

    for (let i = 0; i < COUNT; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 26;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 16;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 14 - 2;
      tempColor.setHex(colors[Math.floor(Math.random() * colors.length)]);
      colArr[i * 3] = tempColor.r;
      colArr[i * 3 + 1] = tempColor.g;
      colArr[i * 3 + 2] = tempColor.b;
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(colArr, 3));

    const points = new THREE.Points(
      geo,
      new THREE.PointsMaterial({
        size: 0.055,
        vertexColors: true,
        transparent: true,
        opacity: isMobile ? 0.55 : 0.7,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        sizeAttenuation: true,
      })
    );
    scene.add(points);

    // Esferas wireframe flotantes (3D visible)
    const makeMesh = (radius, color, x, y, z, wire) => {
      const g = new THREE.IcosahedronGeometry(radius, wire ? 1 : 2);
      const m = new THREE.MeshBasicMaterial({
        color,
        wireframe: wire,
        transparent: true,
        opacity: wire ? 0.16 : 0.06,
      });
      const mesh = new THREE.Mesh(g, m);
      mesh.position.set(x, y, z);
      scene.add(mesh);
      return mesh;
    };

    const meshes = [
      makeMesh(1.7, 0x6366f1, -5.2, 2.6, -4, true),
      makeMesh(1.2, 0x22d3ee, 5.6, -2.4, -5, true),
      makeMesh(0.9, 0x8b5cf6, 4.2, 3.4, -3.5, true),
      makeMesh(2.1, 0x8b5cf6, -4.6, -3.4, -6, true),
    ];

    // Parallax con el mouse
    let tx = 0, ty = 0, mx = 0, my = 0;
    window.addEventListener("pointermove", (e) => {
      tx = (e.clientX / window.innerWidth - 0.5) * 1.6;
      ty = (e.clientY / window.innerHeight - 0.5) * 1.2;
    });

    let t = 0;
    const animate = () => {
      requestAnimationFrame(animate);
      t += 0.004;

      points.rotation.y = t * 0.05;
      points.rotation.x = Math.sin(t * 0.03) * 0.06;

      meshes.forEach((mesh, i) => {
        mesh.rotation.x += 0.0022 + i * 0.0004;
        mesh.rotation.y += 0.0016 + i * 0.0003;
        mesh.position.y += Math.sin(t * (0.5 + i * 0.18) + i) * 0.0014;
      });

      mx += (tx - mx) * 0.04;
      my += (ty - my) * 0.04;
      camera.position.x = mx;
      camera.position.y = -my;
      camera.lookAt(0, 0, 0);

      renderer.render(scene, camera);
    };
    animate();

    window.addEventListener("resize", () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });
  }).catch(() => { /* sin 3D si hay red limitada */ });
})();