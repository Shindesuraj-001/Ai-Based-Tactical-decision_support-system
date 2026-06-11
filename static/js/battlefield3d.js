/*
=================================================================
  ATDSS — static/js/battlefield3d.js  v4.0.1
  UPGRADES:
    ✦ Procedural noise terrain (fBm) with real shadows
    ✦ Smart unit behaviours: patrol / take-cover / retreat
    ✦ Interactive Command Mode (raycast click → move unit)
    ✦ Unit selection with highlight ring
    ✦ Cinematic camera: Free / Top / Follow-unit
    ✦ Mini-map ↔ 3D sync (syncToWorldPosition)
    ✦ Friendly army count driven by API param
    ✦ Units walk on terrain surface
  BUGFIX v4.0.1:
    ✦ Cover: unit now hides BEHIND rock/building (not inside it)
    ✦ Cover: barbed wire excluded as a cover candidate
    ✦ Cover: stopDist=3 keeps unit outside any geometry
    ✦ _moveToward: configurable stop-distance parameter
=================================================================
*/
'use strict';

/* ─────────────────────────────────────────────────────────────
   PROCEDURAL NOISE UTILITIES  (fBm — 6 octaves)
───────────────────────────────────────────────────────────── */
function _hashN(n) {
    const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
    return x - Math.floor(x);
}
function _noise2D(x, z) {
    const xi = Math.floor(x), zi = Math.floor(z);
    const xf = x - xi,       zf = z - zi;
    const u  = xf * xf * (3 - 2 * xf);
    const v  = zf * zf * (3 - 2 * zf);
    const n00 = _hashN(xi     + zi * 57);
    const n10 = _hashN(xi + 1 + zi * 57);
    const n01 = _hashN(xi     + (zi + 1) * 57);
    const n11 = _hashN(xi + 1 + (zi + 1) * 57);
    return n00 + (n10 - n00) * u + (n01 - n00) * v + (n00 - n10 - n01 + n11) * u * v;
}
function _fbm(x, z) {
    let val = 0, amp = 0.5, freq = 1.0, max = 0;
    for (let i = 0; i < 6; i++) {
        val += _noise2D(x * freq, z * freq) * amp;
        max  += amp;
        amp  *= 0.5;
        freq *= 2.1;
    }
    return val / max;  // [0 .. 1]
}

/* Terrain height scales per biome */
const _TERRAIN_H = { desert: 7, forest: 13, urban: 3, mountain: 24 };

/* ─────────────────────────────────────────────────────────────
   GEOMETRY / MATERIAL CACHE
───────────────────────────────────────────────────────────── */
const _GEO_CACHE = {};
const _MAT_CACHE = {};
function _geo(key, factory) {
    if (!_GEO_CACHE[key]) _GEO_CACHE[key] = factory();
    return _GEO_CACHE[key];
}
function _mat(hex, opts = {}) {
    const key = hex + JSON.stringify(opts);
    if (!_MAT_CACHE[key])
        _MAT_CACHE[key] = new THREE.MeshLambertMaterial({ color: hex, ...opts });
    return _MAT_CACHE[key];
}
function _matBasic(hex, opts = {}) {
    const key = 'B' + hex + JSON.stringify(opts);
    if (!_MAT_CACHE[key])
        _MAT_CACHE[key] = new THREE.MeshBasicMaterial({ color: hex, ...opts });
    return _MAT_CACHE[key];
}

/* ─────────────────────────────────────────────────────────────
   RIFLE BUILDER
───────────────────────────────────────────────────────────── */
function _buildRifle(isIndian) {
    const g = new THREE.Group();
    if (isIndian) {
        const rcvMat = _mat(0x222222), stkMat = _mat(0xC8721A), brlMat = _mat(0x1A1A1A);
        const rcv = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.20, 1.85), rcvMat);
        rcv.position.z = 0.55; g.add(rcv);
        const brl = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 1.55, 7), brlMat);
        brl.rotation.x = Math.PI / 2; brl.position.z = 1.85; g.add(brl);
        const gs = new THREE.Mesh(new THREE.BoxGeometry(0.10, 0.16, 0.12), rcvMat);
        gs.position.z = 1.25; g.add(gs);
        const stk = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.18, 0.82), stkMat);
        stk.position.set(0, -0.02, -0.40); g.add(stk);
        const grp = new THREE.Mesh(new THREE.BoxGeometry(0.11, 0.32, 0.13), stkMat);
        grp.position.set(0, -0.22, 0.0); g.add(grp);
        const mag = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.44, 0.16), _mat(0x333300));
        mag.position.set(0, -0.32, 0.38); g.add(mag);
        const sight = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.10, 0.55), rcvMat);
        sight.position.set(0, 0.16, 0.40); g.add(sight);
        const muzzle = new THREE.Object3D(); muzzle.name = 'muzzlePoint'; muzzle.position.z = 2.65; g.add(muzzle);
    } else {
        const rcvMat = _mat(0x1A1A1A), wdMat = _mat(0x8B4513), brlMat = _mat(0x111111);
        const rcv = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.20, 1.70), rcvMat);
        rcv.position.z = 0.45; g.add(rcv);
        const brl = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 1.40, 7), brlMat);
        brl.rotation.x = Math.PI / 2; brl.position.z = 1.70; g.add(brl);
        const stk = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.17, 0.85), wdMat);
        stk.position.set(0, -0.02, -0.43); g.add(stk);
        const grp = new THREE.Mesh(new THREE.BoxGeometry(0.11, 0.30, 0.13), wdMat);
        grp.position.set(0, -0.20, 0.0); g.add(grp);
        const mag = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.48, 0.18), rcvMat);
        mag.position.set(0, -0.32, 0.32); mag.rotation.x = 0.18; g.add(mag);
        const sight = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.10, 0.22), rcvMat);
        sight.position.set(0, 0.16, -0.10); g.add(sight);
        const muzzle = new THREE.Object3D(); muzzle.name = 'muzzlePoint'; muzzle.position.z = 2.45; g.add(muzzle);
    }
    return g;
}

/* ─────────────────────────────────────────────────────────────
   SOLDIER BUILDER
───────────────────────────────────────────────────────────── */
function _buildSoldierGroup(isIndian) {
    const root = new THREE.Group();
    const p    = {};
    const UC = isIndian ? 0x4B5320 : 0x8B7355;
    const HC = isIndian ? 0x3B4218 : 0x555545;
    const VC = isIndian ? 0x556B2F : 0x6B5B3E;
    const SC = 0xC68642, BC = 0x1A1208, GC = isIndian ? 0x6B5420 : 0x4A3A2A;

    /* Head */
    const headPivot = new THREE.Group(); headPivot.position.set(0, 3.80, 0);
    const headMesh  = new THREE.Mesh(new THREE.SphereGeometry(0.45, 8, 7), _mat(SC));
    headMesh.position.y = 0.45; headMesh.castShadow = true; headPivot.add(headMesh);
    const helmDome = new THREE.Mesh(new THREE.SphereGeometry(0.53, 8, 6, 0, Math.PI*2, 0, Math.PI*0.62), _mat(HC));
    helmDome.position.y = 0.58; helmDome.castShadow = true; headPivot.add(helmDome);
    const helmBrim = new THREE.Mesh(new THREE.TorusGeometry(0.52, 0.055, 4, 16), _mat(HC));
    helmBrim.rotation.x = Math.PI / 2; helmBrim.position.y = 0.40; headPivot.add(helmBrim);
    const nose = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.09, 0.12), _mat(SC));
    nose.position.set(0, 0.44, 0.40); headPivot.add(nose);
    root.add(headPivot); p.headPivot = headPivot;

    /* Neck */
    const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.20, 0.34, 6), _mat(SC));
    neck.position.set(0, 3.62, 0); neck.castShadow = true; root.add(neck);

    /* Torso */
    const torsoMesh = new THREE.Mesh(new THREE.BoxGeometry(1.05, 1.50, 0.58), _mat(UC));
    torsoMesh.position.set(0, 2.80, 0); torsoMesh.castShadow = true; torsoMesh.receiveShadow = true; root.add(torsoMesh);
    const vestMesh = new THREE.Mesh(new THREE.BoxGeometry(1.16, 1.05, 0.66), _mat(VC));
    vestMesh.position.set(0, 2.96, 0); vestMesh.castShadow = true; root.add(vestMesh);
    [-0.30, 0, 0.30].forEach(x => {
        const pouch = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.20, 0.22), _mat(GC));
        pouch.position.set(x, 2.24, 0.28); root.add(pouch);
    });
    const belt = new THREE.Mesh(new THREE.BoxGeometry(1.08, 0.12, 0.62), _mat(GC));
    belt.position.set(0, 2.17, 0); root.add(belt);

    /* Left arm */
    const lShoulder = new THREE.Group(); lShoulder.position.set(-0.66, 3.30, 0);
    const lUArm = new THREE.Mesh(new THREE.CylinderGeometry(0.155, 0.145, 0.72, 7), _mat(UC));
    lUArm.position.y = -0.36; lUArm.castShadow = true; lShoulder.add(lUArm);
    const lElbow = new THREE.Group(); lElbow.position.y = -0.72;
    const lFArm = new THREE.Mesh(new THREE.CylinderGeometry(0.130, 0.118, 0.65, 7), _mat(UC));
    lFArm.position.y = -0.32; lFArm.castShadow = true; lElbow.add(lFArm);
    const lHand = new THREE.Mesh(new THREE.BoxGeometry(0.19, 0.17, 0.13), _mat(GC));
    lHand.position.y = -0.67; lElbow.add(lHand);
    lShoulder.add(lElbow); root.add(lShoulder); p.lShoulder = lShoulder; p.lElbow = lElbow;

    /* Right arm */
    const rShoulder = new THREE.Group(); rShoulder.position.set(0.66, 3.30, 0);
    const rUArm = new THREE.Mesh(new THREE.CylinderGeometry(0.155, 0.145, 0.72, 7), _mat(UC));
    rUArm.position.y = -0.36; rUArm.castShadow = true; rShoulder.add(rUArm);
    const rElbow = new THREE.Group(); rElbow.position.y = -0.72;
    const rFArm = new THREE.Mesh(new THREE.CylinderGeometry(0.130, 0.118, 0.65, 7), _mat(UC));
    rFArm.position.y = -0.32; rFArm.castShadow = true; rElbow.add(rFArm);
    const rHand = new THREE.Mesh(new THREE.BoxGeometry(0.19, 0.17, 0.13), _mat(GC));
    rHand.position.y = -0.67; rElbow.add(rHand);
    rShoulder.add(rElbow); root.add(rShoulder); p.rShoulder = rShoulder; p.rElbow = rElbow;

    /* Rifle */
    const rifle = _buildRifle(isIndian);
    rifle.rotation.y = Math.PI;
    rifle.position.set(0.18, 2.60, 0.10);
    root.add(rifle); p.rifleGroup = rifle; p.muzzlePoint = rifle.getObjectByName('muzzlePoint');

    /* Left leg */
    const lHip = new THREE.Group(); lHip.position.set(-0.29, 2.16, 0);
    const lULeg = new THREE.Mesh(new THREE.CylinderGeometry(0.21, 0.19, 0.92, 7), _mat(UC));
    lULeg.position.y = -0.46; lULeg.castShadow = true; lHip.add(lULeg);
    const lKnee = new THREE.Group(); lKnee.position.y = -0.92;
    const lLLeg = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.155, 0.86, 7), _mat(UC));
    lLLeg.position.y = -0.43; lLLeg.castShadow = true; lKnee.add(lLLeg);
    const lBoot = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.28, 0.44), _mat(BC));
    lBoot.position.set(0, -0.88, 0.09); lKnee.add(lBoot);
    lHip.add(lKnee); root.add(lHip); p.lHip = lHip; p.lKnee = lKnee;

    /* Right leg */
    const rHip = new THREE.Group(); rHip.position.set(0.29, 2.16, 0);
    const rULeg = new THREE.Mesh(new THREE.CylinderGeometry(0.21, 0.19, 0.92, 7), _mat(UC));
    rULeg.position.y = -0.46; rULeg.castShadow = true; rHip.add(rULeg);
    const rKnee = new THREE.Group(); rKnee.position.y = -0.92;
    const rLLeg = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.155, 0.86, 7), _mat(UC));
    rLLeg.position.y = -0.43; rLLeg.castShadow = true; rKnee.add(rLLeg);
    const rBoot = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.28, 0.44), _mat(BC));
    rBoot.position.set(0, -0.88, 0.09); rKnee.add(rBoot);
    rHip.add(rKnee); root.add(rHip); p.rHip = rHip; p.rKnee = rKnee;

    /* Health bar */
    const hbCanvas = document.createElement('canvas');
    hbCanvas.width = 128; hbCanvas.height = 18;
    const hbCtx = hbCanvas.getContext('2d');
    const hbTex = new THREE.CanvasTexture(hbCanvas);
    const hbMesh = new THREE.Mesh(
        new THREE.PlaneGeometry(1.4, 0.22),
        new THREE.MeshBasicMaterial({ map: hbTex, transparent: true, depthWrite: false })
    );
    hbMesh.position.set(0, 5.85, 0); hbMesh.name = 'healthBar'; root.add(hbMesh);
    p.hbCanvas = hbCanvas; p.hbCtx = hbCtx; p.hbTex = hbTex; p.hbMesh = hbMesh;

    root.userData = {
        parts: p, health: 100, maxHealth: 100, isDead: false, isShooting: false,
        isIndian: isIndian, shootTimer: 0, shootCooldown: 1.5 + Math.random(),
        engageRange: 55, walkPhase: Math.random() * Math.PI * 2, baseY: 0,
        behaviorState: 'patrol', patrolTarget: null, coverTarget: null,
        commandTarget: null, behaviorTimer: 0, isSelected: false
    };
    _updateHealthBar(root);
    return root;
}

function _updateHealthBar(soldierGroup) {
    const d = soldierGroup.userData, p = d.parts;
    if (!p || !p.hbCtx) return;
    const ctx = p.hbCtx, w = p.hbCanvas.width, h = p.hbCanvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#00000088'; ctx.fillRect(0, 0, w, h);
    const pct = Math.max(0, d.health / d.maxHealth);
    ctx.fillStyle = pct > 0.6 ? '#22c55e' : pct > 0.3 ? '#f59e0b' : '#ef4444';
    ctx.fillRect(2, 3, (w - 4) * pct, h - 6);
    ctx.strokeStyle = '#ffffff44'; ctx.strokeRect(1, 1, w - 2, h - 2);
    p.hbTex.needsUpdate = true;
}

function _animateSoldier(root, delta, t, isMoving) {
    const d = root.userData, p = d.parts;
    if (!p || d.isDead) return;
    d.walkPhase += delta * (isMoving ? 5.5 : 2.0);
    const s = isMoving ? Math.sin(d.walkPhase) * 0.42 : Math.sin(d.walkPhase) * 0.07;
    if (p.lHip)  p.lHip.rotation.x  =  s;
    if (p.rHip)  p.rHip.rotation.x  = -s;
    if (p.lKnee) p.lKnee.rotation.x = isMoving ? Math.max(0,  s) * 0.55 : 0;
    if (p.rKnee) p.rKnee.rotation.x = isMoving ? Math.max(0, -s) * 0.55 : 0;
    if (p.lShoulder) p.lShoulder.rotation.x = -s * 0.5;
    if (p.rShoulder) p.rShoulder.rotation.x =  s * 0.5;
    root.position.y = d.baseY + (isMoving ? Math.abs(Math.sin(d.walkPhase)) * 0.18 : 0);
}

function _applyShotPose(root, recoilStrength) {
    const p = root.userData.parts;
    if (!p) return;
    if (p.rShoulder) p.rShoulder.rotation.x = -0.55 - recoilStrength * 0.3;
    if (p.lShoulder) p.lShoulder.rotation.x = -0.40;
    if (p.lElbow)    p.lElbow.rotation.x    =  0.55;
    if (p.rElbow)    p.rElbow.rotation.x    = -0.10;
}

/* ═══════════════════════════════════════════════════════════════
   MAIN SCENE CLASS  v4.0.0
═══════════════════════════════════════════════════════════════ */
class BattlefieldScene {

    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) throw new Error('BattlefieldScene: container not found');

        this.width  = this.container.clientWidth  || 800;
        this.height = this.container.clientHeight || 500;

        this.scene = this.camera = this.renderer = this.controls = null;
        this.clock = new THREE.Clock();

        this.indianGroups = [];
        this.enemyGroups  = [];
        this.pathLines    = [];
        this.featureObjs  = [];
        this.warLights    = [];
        this.effects      = [];
        this.unitPaths    = [];
        this.unitProgress = [];

        this.killCount     = { indian: 0, enemy: 0 };
        this.onKill        = null;
        this.combatEngaged = false;
        this.objectiveGroup = null;
        this.animFrameId    = null;

        /* ── v4.0 NEW STATE ─────────────────────────────────── */
        this.cameraMode   = 'free';      // 'free' | 'top' | 'follow'
        this.selectedUnit = null;
        this.commandMode  = false;
        this.raycaster    = new THREE.Raycaster();
        this._mouse       = new THREE.Vector2();
        this._terrainType = 'desert';
        this._clickBound  = null;
        /* ────────────────────────────────────────────────────── */

        this.PALETTES = {
            desert:   { sky: 0x87CEEB, ground: 0xC8A060, fog: 0xD4B878, fogD: 0.004 },
            forest:   { sky: 0x3D5E6A, ground: 0x2D5A1B, fog: 0x3D6030, fogD: 0.005 },
            urban:    { sky: 0x8899BB, ground: 0x5A5A6A, fog: 0x7788AA, fogD: 0.003 },
            mountain: { sky: 0x7A9ABB, ground: 0x7A8060, fog: 0x9AABBB, fogD: 0.005 },
        };

        this._init();
    }

    /* ══════════════════════════════════════════════════════════
       INIT
    ══════════════════════════════════════════════════════════ */
    _init() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0d1208);

        this.camera = new THREE.PerspectiveCamera(55, this.width / this.height, 0.3, 2000);
        this.camera.position.set(0, 110, 180);
        this.camera.lookAt(0, 0, 0);

        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.setSize(this.width, this.height);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type    = THREE.PCFSoftShadowMap;
        this.renderer.domElement.style.cssText = 'display:block;width:100%;height:100%';
        this.container.appendChild(this.renderer.domElement);

        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.06;
        this.controls.minDistance   = 20;
        this.controls.maxDistance   = 420;
        this.controls.maxPolarAngle = Math.PI / 2.05;
        this.controls.target.set(0, 0, -20);
        this.controls.update();

        this._addLights();
        this._addGrid();
        this._addCompassLines();

        /* v4 — click handler for selection / command mode */
        this._clickBound = (e) => this._onCanvasClick(e);
        this.renderer.domElement.addEventListener('click', this._clickBound);

        new ResizeObserver(() => this._onResize()).observe(this.container);
        this._renderLoop();
    }

    /* ── Lights (upgraded — stronger sun + fill) ──────────── */
    _addLights() {
        this.scene.add(new THREE.AmbientLight(0x445566, 0.5));

        const sun = new THREE.DirectionalLight(0xFFF5D0, 1.4);
        sun.position.set(80, 200, 60);
        sun.castShadow = true;
        const sc = sun.shadow.camera;
        sc.left = sc.bottom = -180; sc.right = sc.top = 180; sc.far = 700;
        sun.shadow.mapSize.setScalar(2048);
        sun.shadow.bias = -0.0005;
        this.scene.add(sun);

        this.scene.add(new THREE.HemisphereLight(0x5577AA, 0x443322, 0.45));
        this.warLights = [];
    }

    _addFireLight(x, y, z, intensity = 2.5, color = 0xFF5500) {
        const pl = new THREE.PointLight(color, intensity, 45);
        pl.position.set(x, y, z);
        pl.userData.baseIntensity = intensity;
        pl.userData.flicker       = Math.random() * Math.PI * 2;
        this.scene.add(pl);
        this.warLights.push(pl);
        return pl;
    }

    _addGrid() {
        const g = new THREE.GridHelper(200, 20, 0x2A3820, 0x1A2010);
        g.position.y = 0.1; g.name = 'grid';
        this.scene.add(g);
    }
    _addCompassLines() {
        const m = new THREE.LineBasicMaterial({ color: 0x3A5A30, transparent: true, opacity: 0.35 });
        [[[-95, 0.2, 0], [95, 0.2, 0]], [[0, 0.2, -95], [0, 0.2, 95]]].forEach(([a, b]) => {
            const g = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(...a), new THREE.Vector3(...b)]);
            this.scene.add(new THREE.Line(g, m));
        });
    }

    /* ══════════════════════════════════════════════════════════
       TERRAIN HEIGHT QUERY  (pure function — matches build)
    ══════════════════════════════════════════════════════════ */
    getHeightAt(x, z) {
        const hScale = _TERRAIN_H[this._terrainType] || 7;
        let h = (_fbm(x * 0.020, z * 0.020) - 0.45) * hScale * 2;
        /* Crater depressions near objective */
        [[-15, -18], [12, -30], [-8, -45], [20, -20], [0, -10]].forEach(([cx, cz]) => {
            const d2 = (x - cx) ** 2 + (z - cz) ** 2;
            if (d2 < 65) h -= (1 - d2 / 65) * 3.5;
        });
        return Math.max(-4, h);
    }

    /* ══════════════════════════════════════════════════════════
       TERRAIN  — UPGRADED: procedural fBm noise + full shadows
    ══════════════════════════════════════════════════════════ */
    _buildTerrain(terrainType) {
        this._terrainType = terrainType;
        const old = this.scene.getObjectByName('terrain_mesh');
        if (old) { old.geometry.dispose(); old.material.dispose(); this.scene.remove(old); }

        const pal = this.PALETTES[terrainType] || this.PALETTES.desert;
        this.scene.background = new THREE.Color(pal.sky);
        this.scene.fog = new THREE.FogExp2(pal.fog, pal.fogD);

        const SEG = 80;   // higher resolution
        const geo = new THREE.PlaneGeometry(200, 200, SEG, SEG);
        geo.rotateX(-Math.PI / 2);

        const pos = geo.attributes.position;
        for (let i = 0; i < pos.count; i++) {
            const x = pos.getX(i), z = pos.getZ(i);
            pos.setY(i, this.getHeightAt(x, z));
        }
        geo.computeVertexNormals();

        const mesh = new THREE.Mesh(geo, _mat(pal.ground));
        mesh.name = 'terrain_mesh';
        mesh.receiveShadow = true;
        this.scene.add(mesh);
    }

    /* ── War scenery ──────────────────────────────────────── */
    _addBattleScenery(terrain) {
        this.featureObjs.forEach(o => this.scene.remove(o));
        this.featureObjs = [];

        /* Sandbag walls near objective */
        for (let a = 0; a < Math.PI * 2; a += Math.PI / 3) {
            const gp = new THREE.Group();
            const bx = Math.cos(a) * 14, bz = Math.sin(a) * 14 - 40;
            gp.position.set(bx, this.getHeightAt(bx, bz) + 0.6, bz);
            gp.rotation.y = a;
            for (let i = 0; i < 4; i++) {
                for (let j = 0; j < 2; j++) {
                    const sb = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.7, 0.8), _mat(0x9E8050));
                    sb.position.set((i - 1.5) * 1.5, j * 0.7, 0);
                    sb.rotation.y = (Math.random() - 0.5) * 0.15;
                    sb.castShadow = sb.receiveShadow = true;
                    gp.add(sb);
                }
            }
            this.scene.add(gp); this.featureObjs.push(gp);
        }

        /* Barbed wire */
        const wireMat = new THREE.LineBasicMaterial({ color: 0x888888 });
        const wireRadius = 22, wirePoints = [];
        for (let i = 0; i <= 32; i++) {
            const a = (i / 32) * Math.PI * 2;
            const wx = Math.cos(a) * wireRadius, wz = Math.sin(a) * wireRadius - 40;
            wirePoints.push(new THREE.Vector3(wx, this.getHeightAt(wx, wz) + 1.2, wz));
        }
        const wireLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints(wirePoints), wireMat);
        wireLine.userData.isCoverInvalid = true;   // troops must not hide "inside" the wire loop
        this.scene.add(wireLine); this.featureObjs.push(wireLine);

        /* Burned vehicle */
        const vGrp = new THREE.Group();
        vGrp.position.set(25, this.getHeightAt(25, 15) + 0.8, 15);
        vGrp.rotation.y = 0.4;
        const hull = new THREE.Mesh(new THREE.BoxGeometry(4.5, 1.4, 8.5), _mat(0x222222));
        hull.castShadow = hull.receiveShadow = true; vGrp.add(hull);
        const turret = new THREE.Mesh(new THREE.BoxGeometry(2.5, 1.0, 3.0), _mat(0x1A1A1A));
        turret.position.set(0, 1.2, -0.5); turret.castShadow = true; vGrp.add(turret);
        this.scene.add(vGrp); this.featureObjs.push(vGrp);
        this._addFireLight(25, 4, 15, 3.5, 0xFF4400);

        /* Terrain objects */
        const objType = { forest: 'tree', desert: 'rock', urban: 'building', mountain: 'rock' }[terrain] || 'rock';
        for (let i = 0; i < 14; i++) {
            let x, z;
            do { x = (Math.random() - 0.5) * 160; z = (Math.random() - 0.5) * 160; }
            while (Math.abs(x) < 18 && Math.abs(z + 40) < 18);
            const obj = this._makeFeature({ type: objType, x, z, scale: 0.7 + Math.random() * 0.9 });
            if (obj) { this.scene.add(obj); this.featureObjs.push(obj); }
        }
    }

    _makeFeature(f) {
        const s = f.scale || 1;
        const groundY = this.getHeightAt(f.x, f.z);
        switch (f.type) {
            case 'tree': {
                const g = new THREE.Group();
                const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.38*s, 0.62*s, 4*s, 7), _mat(0x5C3D1E));
                trunk.position.y = 2 * s; trunk.castShadow = true; g.add(trunk);
                const top = new THREE.Mesh(new THREE.ConeGeometry(2.6*s, 6.5*s, 8), _mat(0x1F5C0A));
                top.position.y = 7 * s; top.castShadow = true; g.add(top);
                g.position.set(f.x, groundY, f.z); return g;
            }
            case 'building': {
                const h = (5 + Math.random() * 9) * s;
                const m = new THREE.Mesh(new THREE.BoxGeometry(5*s, h, 5*s), _mat(0x8A7A7A));
                m.position.set(f.x, groundY + h / 2, f.z);
                m.castShadow = m.receiveShadow = true; return m;
            }
            case 'rock': {
                const m = new THREE.Mesh(new THREE.DodecahedronGeometry(3.5*s, 0), _mat(0x8A8070));
                m.position.set(f.x, groundY + 1.5 * s, f.z);
                m.rotation.set(Math.random() * 0.5, Math.random() * Math.PI * 2, 0);
                m.castShadow = true; return m;
            }
            default: return null;
        }
    }

    /* ── Objective marker ──────────────────────────────────── */
    _addObjective(pos) {
        const old = this.scene.getObjectByName('objective_group');
        if (old) this.scene.remove(old);
        const g = new THREE.Group(); g.name = 'objective_group';
        const gy = this.getHeightAt(pos.x, pos.z);
        g.position.set(pos.x, gy + 1, pos.z);

        const ringMat = new THREE.MeshBasicMaterial({ color: 0xC8A84B, side: THREE.DoubleSide });
        [{ i: 5, o: 6.5 }, { i: 2.5, o: 4 }].forEach(({ i, o }) => {
            const rm = new THREE.Mesh(new THREE.RingGeometry(i, o, 32), ringMat);
            rm.rotation.x = -Math.PI / 2; g.add(rm);
        });
        const beam = new THREE.Mesh(
            new THREE.CylinderGeometry(0.20, 0.20, 28, 8),
            new THREE.MeshBasicMaterial({ color: 0xFFDD44, transparent: true, opacity: 0.50 })
        );
        beam.position.y = 14; g.add(beam);
        const diamond = new THREE.Mesh(
            new THREE.OctahedronGeometry(2.6, 0),
            new THREE.MeshLambertMaterial({ color: 0xC8A84B, emissive: 0xFFAA00, emissiveIntensity: 0.9 })
        );
        diamond.name = 'obj_diamond'; diamond.position.y = 30; g.add(diamond);
        const pl = new THREE.PointLight(0xFFAA00, 2, 50); pl.position.y = 18; g.add(pl);
        this.scene.add(g);
        this.objectiveGroup = g;
    }

    /* ══════════════════════════════════════════════════════════
       UNIT PLACEMENT
    ══════════════════════════════════════════════════════════ */
    _addIndianArmyUnits(friendlyData) {
        this.indianGroups.forEach(g => this.scene.remove(g));
        this.indianGroups = [];
        this.unitProgress = [];

        friendlyData.forEach((u, i) => {
            const soldier = _buildSoldierGroup(true);
            const groundY = this.getHeightAt(u.x, u.z);
            soldier.position.set(u.x, groundY, u.z);
            soldier.userData.baseY   = groundY;
            soldier.userData.unitIdx = i;
            soldier.userData.unitId  = u.id;
            this.scene.add(soldier);
            this.indianGroups.push(soldier);
            this.unitProgress.push(0);
        });
    }

    _addEnemyUnits(enemyData) {
        this.enemyGroups.forEach(g => this.scene.remove(g));
        this.enemyGroups = [];

        enemyData.forEach(e => {
            const soldier = _buildSoldierGroup(false);
            const groundY = this.getHeightAt(e.x, e.z);
            soldier.position.set(e.x, groundY, e.z);
            soldier.userData.baseY  = groundY;
            soldier.userData.unitId = e.id;
            this.scene.add(soldier);
            this.enemyGroups.push(soldier);
        });
    }

    _addPaths(paths) {
        this.pathLines.forEach(l => this.scene.remove(l));
        this.pathLines = [];
        this.unitPaths = [];
        paths.forEach((path, i) => {
            const pts = path.points.map(p => new THREE.Vector3(p.x, this.getHeightAt(p.x, p.z) + 1.5, p.z));
            const c   = parseInt((path.color || '#22c55e').replace('#', ''), 16);
            const geo = new THREE.BufferGeometry().setFromPoints(pts);
            const ln  = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: c, transparent: true, opacity: 0.55 }));
            this.scene.add(ln);
            this.pathLines.push(ln);
            this.unitPaths[i] = pts;
        });
    }

    /* ══════════════════════════════════════════════════════════
       EFFECTS SYSTEM  (unchanged from v3)
    ══════════════════════════════════════════════════════════ */
    _spawnMuzzleFlash(worldPos) {
        const cone = new THREE.Mesh(
            new THREE.ConeGeometry(0.4, 2.2, 7),
            new THREE.MeshBasicMaterial({ color: 0xFFDD00, transparent: true, opacity: 0.9 })
        );
        cone.position.copy(worldPos); cone.rotation.x = Math.PI / 2;
        this.scene.add(cone);
        const pl = new THREE.PointLight(0xFF8800, 8, 22);
        pl.position.copy(worldPos); this.scene.add(pl);
        this.effects.push({ type: 'muzzle', mesh: cone, light: pl, life: 0.12, maxLife: 0.12 });
    }

    _spawnTracer(from, to) {
        const geo = new THREE.BufferGeometry().setFromPoints([from.clone(), to.clone()]);
        const ln  = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: 0xFFFF88, transparent: true, opacity: 0.85 }));
        this.scene.add(ln);
        this.effects.push({ type: 'tracer', mesh: ln, life: 0.22, maxLife: 0.22 });
    }

    _spawnExplosion(pos) {
        const fireMesh = new THREE.Mesh(
            new THREE.SphereGeometry(3.5, 9, 7),
            new THREE.MeshBasicMaterial({ color: 0xFF5500, transparent: true, opacity: 0.95 })
        );
        fireMesh.position.copy(pos); fireMesh.position.y += 2;
        this.scene.add(fireMesh);
        const pl = new THREE.PointLight(0xFF6600, 18, 60);
        pl.position.copy(fireMesh.position); this.scene.add(pl);
        this.effects.push({ type: 'explosion', mesh: fireMesh, light: pl, life: 0.55, maxLife: 0.55, startScale: 0.3 });

        for (let i = 0; i < 14; i++) {
            const deb = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.3, 0.3), new THREE.MeshLambertMaterial({ color: 0x444444 }));
            deb.position.copy(pos); deb.position.y += 1.5;
            deb.castShadow = true; this.scene.add(deb);
            this.effects.push({ type: 'debris', mesh: deb, life: 1.2, maxLife: 1.2, vx: (Math.random()-0.5)*30, vy: 10+Math.random()*14, vz: (Math.random()-0.5)*30, gravity: -18 });
        }

        const smoke = new THREE.Mesh(
            new THREE.SphereGeometry(2.5, 7, 5),
            new THREE.MeshBasicMaterial({ color: 0x555555, transparent: true, opacity: 0.70 })
        );
        smoke.position.copy(pos); smoke.position.y += 3;
        this.scene.add(smoke);
        this.effects.push({ type: 'smoke', mesh: smoke, life: 3.5, maxLife: 3.5 });
    }

    _updateEffects(delta) {
        for (let i = this.effects.length - 1; i >= 0; i--) {
            const e = this.effects[i];
            e.life -= delta;
            if (e.life <= 0) {
                this.scene.remove(e.mesh);
                if (e.light) this.scene.remove(e.light);
                this.effects.splice(i, 1);
                continue;
            }
            const frac = e.life / e.maxLife;
            if (e.type === 'muzzle') {
                e.mesh.material.opacity = frac * 0.9;
                if (e.light) e.light.intensity = frac * 8;
            } else if (e.type === 'tracer') {
                e.mesh.material.opacity = frac * 0.85;
            } else if (e.type === 'explosion') {
                e.mesh.scale.setScalar(e.startScale + (1 - frac) * 3.5);
                e.mesh.material.opacity = frac * 0.95;
                if (e.light) e.light.intensity = frac * 18;
            } else if (e.type === 'debris') {
                e.vy += e.gravity * delta;
                e.mesh.position.x += e.vx * delta;
                e.mesh.position.y += e.vy * delta;
                e.mesh.position.z += e.vz * delta;
                const groundY = this.getHeightAt(e.mesh.position.x, e.mesh.position.z);
                if (e.mesh.position.y < groundY) {
                    e.mesh.position.y = groundY;
                    e.vy *= -0.25; e.vx *= 0.7; e.vz *= 0.7;
                }
            } else if (e.type === 'smoke') {
                e.mesh.scale.setScalar(1 + (1 - frac) * 2.5);
                e.mesh.position.y += delta * 1.8;
                e.mesh.material.opacity = frac * 0.65;
            }
        }
    }

    /* ══════════════════════════════════════════════════════════
       COMBAT SYSTEM  (unchanged from v3)
    ══════════════════════════════════════════════════════════ */
    _updateCombat(delta) {
        const living = this.enemyGroups.filter(e => !e.userData.isDead);
        const friendlyLiving = this.indianGroups.filter(f => !f.userData.isDead);
        if (!living.length || !friendlyLiving.length) return;

        friendlyLiving.forEach(friendly => {
            const fu = friendly.userData;
            fu.shootTimer = Math.max(0, fu.shootTimer - delta);
            let nearest = null, nearestDist = Infinity;
            living.forEach(enemy => {
                const d = friendly.position.distanceTo(enemy.position);
                if (d < nearestDist) { nearestDist = d; nearest = enemy; }
            });
            if (!nearest) return;
            if (nearestDist < fu.engageRange) {
                const dir = nearest.position.clone().sub(friendly.position).normalize();
                friendly.rotation.y = Math.atan2(dir.x, dir.z);
                fu.isShooting = true;
                _applyShotPose(friendly, Math.max(0, 1 - fu.shootTimer / fu.shootCooldown));
                if (fu.shootTimer <= 0) { fu.shootTimer = fu.shootCooldown; this._fireWeapon(friendly, nearest); }
            } else {
                fu.isShooting = false;
            }
        });

        living.forEach(enemy => {
            const eu = enemy.userData;
            eu.shootTimer = Math.max(0, eu.shootTimer - delta);
            let nearest = null, nearestDist = Infinity;
            friendlyLiving.forEach(f => {
                const d = enemy.position.distanceTo(f.position);
                if (d < nearestDist) { nearestDist = d; nearest = f; }
            });
            if (!nearest) return;
            if (nearestDist < eu.engageRange) {
                const dir = nearest.position.clone().sub(enemy.position).normalize();
                enemy.rotation.y = Math.atan2(dir.x, dir.z);
                eu.isShooting = true;
                _applyShotPose(enemy, Math.max(0, 1 - eu.shootTimer / eu.shootCooldown));
                if (eu.shootTimer <= 0) { eu.shootTimer = eu.shootCooldown; this._fireWeapon(enemy, nearest); }
            } else {
                eu.isShooting = false;
            }
        });
    }

    _fireWeapon(shooter, target) {
        const muzzleLocal = shooter.userData.parts.muzzlePoint;
        const muzzlePos   = new THREE.Vector3();
        if (muzzleLocal) muzzleLocal.getWorldPosition(muzzlePos);
        else { muzzlePos.copy(shooter.position); muzzlePos.y += 2.8; }
        const targetPos = target.position.clone(); targetPos.y += 2.4;
        this._spawnMuzzleFlash(muzzlePos);
        this._spawnTracer(muzzlePos, targetPos);
        const dmg = 8 + Math.random() * 12;
        target.userData.health = Math.max(0, target.userData.health - dmg);
        _updateHealthBar(target);
        if (target.userData.health <= 0 && !target.userData.isDead) {
            target.userData.isDead = true;
            this._killUnit(target);
        }
    }

    _killUnit(unit) {
        const isIndianUnit = unit.userData.isIndian;
        if (isIndianUnit) this.killCount.enemy++;
        else              this.killCount.indian++;
        unit.rotation.z = (Math.random() > 0.5 ? 1 : -1) * Math.PI / 2;
        unit.position.y -= 1.5;
        const hb = unit.userData.parts.hbMesh;
        if (hb) hb.visible = false;
        /* Deselect if killed */
        if (unit === this.selectedUnit) this.clearSelection();
        this._spawnExplosion(unit.position.clone());
        if (typeof this.onKill === 'function') this.onKill(this.killCount);
    }

    /* ══════════════════════════════════════════════════════════
       v4 — SMART UNIT BEHAVIOURS
    ══════════════════════════════════════════════════════════ */
    _updateBehaviors(delta) {
        const living = this.enemyGroups.filter(e => !e.userData.isDead);

        /* ── Friendly unit AI ─────────────────────────────── */
        this.indianGroups.forEach(unit => {
            const ud = unit.userData;
            if (ud.isDead || ud.isShooting) return;

            /* Human command target always wins */
            if (ud.commandTarget) {
                this._moveToward(unit, ud.commandTarget, 18, delta);
                if (unit.position.distanceTo(ud.commandTarget) < 1.5) ud.commandTarget = null;
                return;
            }

            /* Find nearest enemy */
            let nearestEnemy = null, minDist = Infinity;
            living.forEach(e => {
                const d = unit.position.distanceTo(e.position);
                if (d < minDist) { minDist = d; nearestEnemy = e; }
            });

            /* State machine */
            ud.behaviorTimer = (ud.behaviorTimer || 0) - delta;
            const prevState = ud.behaviorState;

            if (ud.health < 30) {
                ud.behaviorState = 'retreat';
            } else if (nearestEnemy && minDist < ud.engageRange * 1.8 && minDist > ud.engageRange) {
                ud.behaviorState = 'cover';
            } else {
                ud.behaviorState = 'patrol';
            }

            if (ud.behaviorState !== prevState) {
                ud.patrolTarget = null; ud.coverTarget = null; ud.behaviorTimer = 0;
            }

            if (ud.behaviorState === 'patrol') {
                this._doBehaviorPatrol(unit, delta);
            } else if (ud.behaviorState === 'cover') {
                this._doBehaviorCover(unit, delta, nearestEnemy);
            } else if (ud.behaviorState === 'retreat' && nearestEnemy) {
                this._doBehaviorRetreat(unit, delta, nearestEnemy);
            }
        });

        /* ── Enemy retreat when critically wounded ────────── */
        const friendlyLiving = this.indianGroups.filter(f => !f.userData.isDead);
        this.enemyGroups.forEach(unit => {
            const ud = unit.userData;
            if (ud.isDead || ud.isShooting || ud.health > 25) return;
            let nearestFriendly = null, minDist = Infinity;
            friendlyLiving.forEach(f => {
                const d = unit.position.distanceTo(f.position);
                if (d < minDist) { minDist = d; nearestFriendly = f; }
            });
            if (nearestFriendly) this._doBehaviorRetreat(unit, delta, nearestFriendly);
        });
    }

    _doBehaviorPatrol(unit, delta) {
        const ud = unit.userData;
        if (ud.behaviorTimer > 0 && !ud.patrolTarget) return; // waiting between patrols

        if (!ud.patrolTarget) {
            const angle  = Math.random() * Math.PI * 2;
            const radius = 12 + Math.random() * 22;
            const tx = Math.max(-85, Math.min(85, unit.position.x + Math.cos(angle) * radius));
            const tz = Math.max(-85, Math.min(85, unit.position.z + Math.sin(angle) * radius));
            ud.patrolTarget = new THREE.Vector3(tx, this.getHeightAt(tx, tz), tz);
            ud.behaviorTimer = 2 + Math.random() * 3;
        }

        const dist = unit.position.distanceTo(ud.patrolTarget);
        if (dist < 2) {
            ud.patrolTarget = null;
            ud.behaviorTimer = 1 + Math.random() * 2; // pause before next
            return;
        }
        this._moveToward(unit, ud.patrolTarget, 7, delta);
    }

    _doBehaviorCover(unit, delta, nearestEnemy) {
        const ud = unit.userData;

        if (!ud.coverTarget || ud.behaviorTimer <= 0) {
            let bestCover = null, bestDist = Infinity;

            this.featureObjs.forEach(obj => {
                /* Skip Lines (barbed wire) — they have no solid volume */
                if (!obj.position || obj.isLine || obj.type === 'Line') return;
                if (obj.userData && obj.userData.isCoverInvalid) return;

                const d = unit.position.distanceTo(obj.position);
                /* Must be reachable (< 55) and not already on top of it (> 4) */
                if (d < bestDist && d < 55 && d > 4) {
                    bestDist = d;
                    bestCover = obj;
                }
            });

            if (bestCover) {
                /*
                 * Compute the SAFE SIDE POSITION:
                 *   Direction = from the threat TOWARD the cover object.
                 *   We place the unit on THAT same side so the rock/building
                 *   sits between the unit and the enemy — and we offset far
                 *   enough that the unit stays outside the geometry.
                 *
                 *   Rough cover radius by object type:
                 *     THREE.Group (sandbags / vehicle)  → 5 units
                 *     Mesh with BoxGeometry (building)  → 4.5 units
                 *     Mesh with DodecahedronGeometry    → 4 units  (rock)
                 *     Mesh with ConeGeometry (tree top) → 3.5 units
                 *   We use a conservative default of 5.5 so we never clip.
                 */
                const threatPos = (nearestEnemy && nearestEnemy.position)
                    ? nearestEnemy.position
                    : new THREE.Vector3(0, 0, -40);   // fallback: objective area

                /* Direction from threat toward cover */
                const dir = new THREE.Vector3()
                    .subVectors(bestCover.position, threatPos)
                    .normalize();

                /* Estimate radius: Groups (sandbags/vehicle) are wider */
                const coverRadius = (bestCover.isGroup || bestCover.type === 'Group') ? 6.0 : 5.0;

                /* Target sits on the far side of the cover from the enemy */
                const tx = Math.max(-85, Math.min(85, bestCover.position.x + dir.x * coverRadius));
                const tz = Math.max(-85, Math.min(85, bestCover.position.z + dir.z * coverRadius));

                ud.coverTarget  = new THREE.Vector3(tx, this.getHeightAt(tx, tz), tz);
                ud.behaviorTimer = 3.5;
            }
        }

        if (ud.coverTarget) {
            /* Stop 3 units from target centre — keeps unit outside any geometry */
            this._moveToward(unit, ud.coverTarget, 13, delta, 3.0);

            /* While in cover, face the enemy */
            if (nearestEnemy && nearestEnemy.position) {
                unit.rotation.y = Math.atan2(
                    nearestEnemy.position.x - unit.position.x,
                    nearestEnemy.position.z - unit.position.z
                );
            }
        }
    }

    _doBehaviorRetreat(unit, delta, nearestThreat) {
        const dir = new THREE.Vector3().subVectors(unit.position, nearestThreat.position).normalize();
        const tx  = Math.max(-85, Math.min(85, unit.position.x + dir.x * 25));
        const tz  = Math.max(-85, Math.min(85, unit.position.z + dir.z * 25));
        const tgt = new THREE.Vector3(tx, this.getHeightAt(tx, tz), tz);
        this._moveToward(unit, tgt, 16, delta);
    }

    /* Generic unit movement toward a Vector3.
     * stopDist: how many units from the target before stopping (default 1.5).
     * Cover calls pass 3.0 so units halt outside rock/building geometry. */
    _moveToward(unit, target, speed, delta, stopDist = 1.5) {
        const dx   = target.x - unit.position.x;
        const dz   = target.z - unit.position.z;
        const dist = Math.sqrt(dx * dx + dz * dz);
        if (dist < stopDist) return;
        const nx = dx / dist, nz = dz / dist;
        unit.position.x += nx * speed * delta;
        unit.position.z += nz * speed * delta;
        unit.position.y = this.getHeightAt(unit.position.x, unit.position.z);
        unit.userData.baseY = unit.position.y;
        unit.rotation.y = Math.atan2(nx, nz);
        _animateSoldier(unit, delta, 0, true);
    }

    /* ══════════════════════════════════════════════════════════
       v4 — INTERACTIVE COMMAND MODE  (raycast)
    ══════════════════════════════════════════════════════════ */
    _onCanvasClick(event) {
        const rect = this.renderer.domElement.getBoundingClientRect();
        this._mouse.x = ((event.clientX - rect.left) / rect.width)  *  2 - 1;
        this._mouse.y = ((event.clientY - rect.top)  / rect.height) * -2 + 1;
        this.raycaster.setFromCamera(this._mouse, this.camera);

        /* 1) Check if clicking on a friendly unit → select */
        const unitMeshes = [];
        this.indianGroups.filter(u => !u.userData.isDead).forEach(u =>
            u.traverse(child => { if (child.isMesh) { child._unitRoot = u; unitMeshes.push(child); } })
        );
        const unitHits = this.raycaster.intersectObjects(unitMeshes, false);
        if (unitHits.length > 0 && unitHits[0].object._unitRoot) {
            this.selectUnit(unitHits[0].object._unitRoot);
            return;
        }

        /* 2) Command mode + selected unit → move to terrain point */
        if (this.commandMode && this.selectedUnit && !this.selectedUnit.userData.isDead) {
            const terrain = this.scene.getObjectByName('terrain_mesh');
            if (terrain) {
                const hits = this.raycaster.intersectObject(terrain);
                if (hits.length > 0) {
                    const pt = hits[0].point;
                    this.selectedUnit.userData.commandTarget = pt.clone();
                    this._spawnCommandMarker(pt);
                    return;
                }
            }
        }

        /* 3) Click empty space → deselect */
        this.clearSelection();
    }

    selectUnit(unit) {
        this.clearSelection();
        this.selectedUnit = unit;
        unit.userData.isSelected = true;
        /* Add glowing ring at feet */
        const ring = new THREE.Mesh(
            new THREE.RingGeometry(1.1, 1.7, 20),
            new THREE.MeshBasicMaterial({ color: 0x00FF88, side: THREE.DoubleSide, transparent: true, opacity: 0.85 })
        );
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = 0.15;
        ring.name = 'selectionRing';
        unit.add(ring);
        if (typeof this.onUnitSelected === 'function') this.onUnitSelected(unit);
    }

    clearSelection() {
        if (this.selectedUnit) {
            const ring = this.selectedUnit.getObjectByName('selectionRing');
            if (ring) this.selectedUnit.remove(ring);
            this.selectedUnit.userData.isSelected = false;
            this.selectedUnit = null;
        }
    }

    _spawnCommandMarker(pos) {
        const old = this.scene.getObjectByName('cmdMarker');
        if (old) this.scene.remove(old);
        const ring = new THREE.Mesh(
            new THREE.RingGeometry(0.4, 1.1, 20),
            new THREE.MeshBasicMaterial({ color: 0x00FFFF, side: THREE.DoubleSide, transparent: true, opacity: 0.9 })
        );
        ring.rotation.x = -Math.PI / 2;
        ring.position.copy(pos); ring.position.y += 0.25;
        ring.name = 'cmdMarker';
        this.scene.add(ring);
        setTimeout(() => {
            if (this.scene.getObjectByName('cmdMarker') === ring) this.scene.remove(ring);
        }, 2200);
    }

    setCommandMode(active) {
        this.commandMode = active;
        /* Update cursor */
        this.renderer.domElement.style.cursor = active ? 'crosshair' : 'default';
    }

    /* ══════════════════════════════════════════════════════════
       v4 — CINEMATIC CAMERA SYSTEM
    ══════════════════════════════════════════════════════════ */
    setCameraMode(mode) {
        this.cameraMode = mode;
        if (mode === 'free') {
            this.controls.enabled = true;
            this.controls.update();
        } else if (mode === 'top') {
            this.controls.enabled = false;
            /* Smooth top-down */
            this.camera.position.set(0, 280, 0.01);
            this.camera.lookAt(0, 0, 0);
            this.controls.target.set(0, 0, 0);
        } else if (mode === 'follow') {
            this.controls.enabled = false;
            if (!this.selectedUnit) {
                /* Auto-select first living unit */
                const first = this.indianGroups.find(u => !u.userData.isDead);
                if (first) this.selectUnit(first);
            }
        }
    }

    _updateCameraMode(delta) {
        if (this.cameraMode !== 'follow') return;
        const target = this.selectedUnit && !this.selectedUnit.userData.isDead
            ? this.selectedUnit
            : this.indianGroups.find(u => !u.userData.isDead);
        if (!target) return;

        const pos = target.position;
        /* Camera floats behind and above selected unit */
        const behind = new THREE.Vector3(
            Math.sin(target.rotation.y) * 28,
            20,
            Math.cos(target.rotation.y) * 28
        );
        const desired = pos.clone().add(behind);
        this.camera.position.lerp(desired, Math.min(1, delta * 4));

        /* Look-at point slightly ahead of unit */
        const lookPt = pos.clone().add(new THREE.Vector3(0, 3, 0));
        this.camera.lookAt(lookPt);
    }

    /* ══════════════════════════════════════════════════════════
       v4 — MAP ↔ 3D SYNCHRONISATION
       Convert world-space x,z (relative to scene centre) to
       camera position so the same area is visible.
    ══════════════════════════════════════════════════════════ */
    syncToWorldPosition(x, z) {
        const target = new THREE.Vector3(x, this.getHeightAt(x, z), z);
        this.camera.position.set(x, 90, z + 70);
        this.controls.target.copy(target);
        this.controls.update();
    }

    /**
     * Convert lat/lng offsets from a map centre to 3D x,z.
     * mapCenterLat, mapCenterLng = lat/lng that corresponds to 3D (0,0).
     * scale: how many 3D units per degree (default 500).
     */
    syncFromLatLng(lat, lng, mapCenterLat, mapCenterLng, scale = 500) {
        const x = (lng - mapCenterLng) * scale;
        const z = -(lat - mapCenterLat) * scale;
        this.syncToWorldPosition(x, z);
    }

    /* ══════════════════════════════════════════════════════════
       RENDER LOOP
    ══════════════════════════════════════════════════════════ */
    _renderLoop() {
        this.animFrameId = requestAnimationFrame(() => this._renderLoop());
        const delta = Math.min(this.clock.getDelta(), 0.05);
        const t     = this.clock.getElapsedTime();

        if (this.cameraMode === 'free') this.controls.update();

        this._animateUnits(delta, t);
        this._updateCombat(delta);
        this._updateBehaviors(delta);
        this._updateCameraMode(delta);
        this._updateEffects(delta);
        this._flickerLights(t);
        this._billboardHealthBars();

        /* Objective diamond spin */
        if (this.objectiveGroup) {
            const d = this.objectiveGroup.getObjectByName('obj_diamond');
            if (d) { d.rotation.y += delta * 1.7; d.rotation.x += delta * 0.55; }
        }

        /* Command marker pulse */
        const cm = this.scene.getObjectByName('cmdMarker');
        if (cm) cm.material.opacity = 0.5 + 0.4 * Math.sin(t * 8);

        this.renderer.render(this.scene, this.camera);
    }

    _flickerLights(t) {
        this.warLights.forEach(pl => {
            pl.userData.flicker += 0.08;
            const flicker = Math.sin(pl.userData.flicker * 8.5) * 0.35 + Math.sin(pl.userData.flicker * 3.2) * 0.18;
            pl.intensity = pl.userData.baseIntensity * (1 + flicker);
        });
    }

    _animateUnits(delta, t) {
        const SPEED = 0.028;

        /* Indian Army — path animation + terrain height */
        this.indianGroups.forEach((g, i) => {
            if (g.userData.isDead) return;
            const ud   = g.userData;

            /* Command target handled by _updateBehaviors; skip path if commandTarget set */
            if (ud.commandTarget || ud.behaviorState === 'cover' || ud.behaviorState === 'retreat') return;

            if (ud.isShooting) { _animateSoldier(g, delta, t, false); return; }

            const path = this.unitPaths[i];
            if (path && path.length >= 2) {
                this.unitProgress[i] = ((this.unitProgress[i] || 0) + delta * SPEED) % 1;
                const p   = this.unitProgress[i];
                const seg = Math.min(Math.floor(p * (path.length - 1)), path.length - 2);
                const st  = (p * (path.length - 1)) % 1;
                const a = path[seg], b = path[seg + 1];
                g.position.x = a.x + (b.x - a.x) * st;
                g.position.z = a.z + (b.z - a.z) * st;
                g.position.y = this.getHeightAt(g.position.x, g.position.z);
                ud.baseY = g.position.y;
                const dx = b.x - a.x, dz = b.z - a.z;
                if (Math.abs(dx) + Math.abs(dz) > 0.01) g.rotation.y = Math.atan2(dx, dz);
                _animateSoldier(g, delta, t, true);
            } else {
                _animateSoldier(g, delta, t, false);
            }
        });

        /* Enemy — patrol wobble + terrain height */
        this.enemyGroups.forEach((g, i) => {
            if (g.userData.isDead || g.userData.isShooting) return;
            if (g.userData.health <= 25) return; // retreat handled by behaviors
            g.position.x += Math.cos(t * 0.4 + i) * delta * 0.35;
            g.position.z += Math.sin(t * 0.4 + i) * delta * 0.35;
            g.position.y = this.getHeightAt(g.position.x, g.position.z);
            g.userData.baseY = g.position.y;
            _animateSoldier(g, delta, t, true);
        });
    }

    _billboardHealthBars() {
        [...this.indianGroups, ...this.enemyGroups].forEach(u => {
            const hb = u.getObjectByName('healthBar');
            if (hb) hb.quaternion.copy(this.camera.quaternion);
        });
    }

    /* ══════════════════════════════════════════════════════════
       PUBLIC API
    ══════════════════════════════════════════════════════════ */
    async loadData(terrain, enemyCount, strategyType, friendlyCount = 8) {
        const url = `/api/battlefield_data?terrain=${terrain}&enemy_count=${enemyCount}&strategy_type=${strategyType}&friendly_count=${friendlyCount}`;
        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        if (data.status !== 'success') throw new Error(data.message || 'API error');

        /* Reset */
        this.effects.forEach(e => { this.scene.remove(e.mesh); if (e.light) this.scene.remove(e.light); });
        this.effects = [];
        this.warLights.forEach(l => this.scene.remove(l));
        this.warLights = [];
        this.killCount = { indian: 0, enemy: 0 };
        this.clearSelection();

        this._buildTerrain(data.terrain);
        this._addBattleScenery(data.terrain);
        this._addObjective(data.objective);
        this._addIndianArmyUnits(data.friendly);
        this._addEnemyUnits(data.enemies);
        this._addPaths(data.paths);

        return data;
    }

    /* Camera presets */
    resetCamera()    { this.cameraMode = 'free'; this.controls.enabled = true; this.camera.position.set(0, 110, 180); this.controls.target.set(0, 0, -20); this.controls.update(); }
    topView()        { this.setCameraMode('top'); }
    sideView()       { this.cameraMode = 'free'; this.controls.enabled = true; this.camera.position.set(200, 55, 0); this.controls.target.set(0, 0, 0); this.controls.update(); }
    focusObjective() { this.cameraMode = 'free'; this.controls.enabled = true; this.camera.position.set(0, 70, 55); this.controls.target.set(0, 10, -40); this.controls.update(); }

    _onResize() {
        const w = this.container.clientWidth, h = this.container.clientHeight;
        if (!w || !h) return;
        this.camera.aspect = w / h;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(w, h);
    }

    destroy() {
        if (this.animFrameId) cancelAnimationFrame(this.animFrameId);
        if (this._clickBound) this.renderer.domElement.removeEventListener('click', this._clickBound);
        this.renderer.dispose();
        if (this.container.contains(this.renderer.domElement))
            this.container.removeChild(this.renderer.domElement);
    }
}