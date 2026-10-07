import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.module.js'

const canvas = document.querySelector('#care-scene')
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
document.documentElement.classList.add('no-webgl')

if (canvas && 'WebGLRenderingContext' in window) {
  try {
    document.documentElement.classList.remove('no-webgl')
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: 'low-power' })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.7))
    renderer.setSize(window.innerWidth, window.innerHeight, false)
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.15

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(34, window.innerWidth / window.innerHeight, 0.1, 80)
    camera.position.set(0, 0, 10.8)
    scene.add(new THREE.HemisphereLight(0xf4f6ec, 0x52635c, 2.1))

    const keyLight = new THREE.DirectionalLight(0xffffff, 3.2)
    keyLight.position.set(-3, 5, 8)
    scene.add(keyLight)
    const rimLight = new THREE.PointLight(0x66c4a7, 28, 18)
    rimLight.position.set(3.5, -2.5, 3)
    scene.add(rimLight)

    const system = new THREE.Group()
    scene.add(system)
    const loop = new THREE.Group()
    system.add(loop)

    const mainRing = new THREE.Mesh(
      new THREE.TorusGeometry(2.6, 0.025, 10, 180),
      new THREE.MeshStandardMaterial({ color: 0x177663, metalness: 0.52, roughness: 0.32 })
    )
    loop.add(mainRing)
    const crossRing = new THREE.Mesh(
      new THREE.TorusGeometry(2.15, 0.012, 8, 150),
      new THREE.MeshStandardMaterial({ color: 0xbd563f, metalness: 0.35, roughness: 0.4, transparent: true, opacity: 0.72 })
    )
    crossRing.rotation.set(0.8, 0.2, 0.52)
    loop.add(crossRing)

    const core = new THREE.Mesh(
      new THREE.IcosahedronGeometry(0.54, 2),
      new THREE.MeshPhysicalMaterial({ color: 0xd4ea70, metalness: 0.28, roughness: 0.18, clearcoat: 1, clearcoatRoughness: 0.15 })
    )
    loop.add(core)

    function labelTexture(title, detail, color) {
      const surface = document.createElement('canvas')
      surface.width = 512
      surface.height = 320
      const context = surface.getContext('2d')
      context.fillStyle = '#f9faf5'
      context.beginPath()
      context.roundRect(0, 0, 512, 320, 22)
      context.fill()
      context.fillStyle = color
      context.fillRect(0, 0, 11, 320)
      context.fillStyle = '#63746d'
      context.font = '500 25px DM Mono, monospace'
      context.fillText('CARELOOP   /   NEXT STEP', 38, 65)
      context.fillStyle = '#143c35'
      context.font = '600 47px DM Sans, sans-serif'
      context.fillText(title, 38, 143)
      context.fillStyle = '#596a61'
      context.font = '400 27px DM Sans, sans-serif'
      context.fillText(detail, 38, 199)
      context.fillStyle = color
      context.beginPath()
      context.arc(460, 264, 13, 0, Math.PI * 2)
      context.fill()
      const texture = new THREE.CanvasTexture(surface)
      texture.colorSpace = THREE.SRGBColorSpace
      return texture
    }

    const cardData = [
      { title: 'MRI scan', detail: 'Book the brain scan', color: '#177663', angle: 0.38 },
      { title: 'Referral', detail: 'Neurology follow-up', color: '#bd563f', angle: 2.46 },
      { title: 'Check-in', detail: 'Review the results', color: '#718a3d', angle: 4.3 },
    ]
    const cards = cardData.map((item, index) => {
      const card = new THREE.Group()
      const body = new THREE.Mesh(
        new THREE.BoxGeometry(1.8, 1.12, 0.11),
        new THREE.MeshPhysicalMaterial({ color: 0xf9faf5, metalness: 0.06, roughness: 0.35, clearcoat: 0.8 })
      )
      card.add(body)
      const face = new THREE.Mesh(
        new THREE.PlaneGeometry(1.72, 1.02),
        new THREE.MeshBasicMaterial({ map: labelTexture(item.title, item.detail, item.color), toneMapped: false })
      )
      face.position.z = 0.061
      card.add(face)
      const angle = item.angle
      card.position.set(Math.cos(angle) * 2.9, Math.sin(angle) * 2.12, index === 1 ? 0.45 : 0.1)
      card.rotation.z = Math.sin(angle) * 0.06
      card.userData.baseZ = card.position.z
      loop.add(card)
      return card
    })

    const beads = Array.from({ length: 9 }, (_, index) => {
      const angle = (index / 9) * Math.PI * 2
      const bead = new THREE.Mesh(
        new THREE.SphereGeometry(index % 3 === 0 ? 0.095 : 0.055, 20, 16),
        new THREE.MeshStandardMaterial({ color: index % 3 === 0 ? 0xbd563f : 0x177663, emissive: 0x124b40, emissiveIntensity: 0.18, roughness: 0.26 })
      )
      bead.position.set(Math.cos(angle) * 2.6, Math.sin(angle) * 2.6, 0.03)
      loop.add(bead)
      return bead
    })

    const poses = [
      { x: 2.3, y: 0, scale: 0.92, tilt: 0.05, turn: -0.12 },
      { x: 2.55, y: 0.12, scale: 1.03, tilt: 0.1, turn: 0.02 },
      { x: 2.18, y: -0.06, scale: 1.12, tilt: 0.14, turn: 0.16 },
      { x: 2.48, y: 0.08, scale: 0.96, tilt: 0.08, turn: 0.3 },
      { x: 1.95, y: -0.02, scale: 1.14, tilt: 0.16, turn: 0.42 },
      { x: 2.26, y: 0.1, scale: 1.05, tilt: 0.1, turn: 0.56 },
    ]
    let activeScene = 0
    let pointerX = 0
    let pointerY = 0
    let frame = 0
    const timer = new THREE.Timer()
    const clamp = (value, min, max) => Math.min(max, Math.max(min, value))
    const mix = (start, end, amount) => start + (end - start) * amount

    function resize() {
      const width = window.innerWidth
      const height = window.innerHeight
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.7))
      renderer.setSize(width, height, false)
      camera.aspect = width / height
      camera.updateProjectionMatrix()
      const mobile = width < 760
      system.scale.setScalar(mobile ? 0.67 : 0.94)
      system.position.x = mobile ? 0.65 : 2.25
      if (reducedMotion) renderStatic()
    }

    function draw() {
      timer.update()
      const elapsed = timer.getElapsed()
      const pose = poses[activeScene] ?? poses[0]
      const mobile = window.innerWidth < 760
      const targetX = mobile ? 0.5 : pose.x
      system.position.x = mix(system.position.x, targetX + pointerX * 0.12, 0.035)
      system.position.y = mix(system.position.y, pose.y + pointerY * 0.08, 0.035)
      system.scale.lerp(new THREE.Vector3(mobile ? 0.67 : pose.scale, mobile ? 0.67 : pose.scale, mobile ? 0.67 : pose.scale), 0.035)
      loop.rotation.x = mix(loop.rotation.x, pose.tilt + pointerY * 0.08, 0.035)
      loop.rotation.y = mix(loop.rotation.y, pose.turn + Math.sin(elapsed * 0.18) * 0.06, 0.035)
      loop.rotation.z = mix(loop.rotation.z, Math.sin(elapsed * 0.22) * 0.045 + pointerX * 0.035, 0.035)
      core.rotation.x += reducedMotion ? 0 : 0.003
      core.rotation.y += reducedMotion ? 0 : 0.005
      cards.forEach((card, index) => {
        card.position.z = card.userData.baseZ + Math.sin(elapsed * 0.7 + index * 1.8) * 0.13
        card.rotation.y = Math.sin(elapsed * 0.24 + index) * 0.09
      })
      beads.forEach((bead, index) => {
        const pulse = 1 + Math.sin(elapsed * 1.3 + index * 0.8) * 0.1
        bead.scale.setScalar(pulse)
      })
      renderer.render(scene, camera)
    }

    function renderStatic() {
      if (!renderer) return
      draw()
    }

    function animate() {
      frame = window.requestAnimationFrame(animate)
      if (!document.hidden) draw()
    }

    const chapters = [...document.querySelectorAll('[data-scene]')]
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          activeScene = Number(entry.target.dataset.scene) || 0
          if (reducedMotion) renderStatic()
        }
      }
    }, { threshold: 0.48 })
    chapters.forEach((chapter) => observer.observe(chapter))

    window.addEventListener('resize', resize, { passive: true })
    window.addEventListener('pointermove', (event) => {
      pointerX = clamp((event.clientX / window.innerWidth - 0.5) * 2, -1, 1)
      pointerY = clamp((event.clientY / window.innerHeight - 0.5) * 2, -1, 1)
    }, { passive: true })

    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible')
          revealObserver.unobserve(entry.target)
        }
      })
    }, { threshold: 0.14 })
    document.querySelectorAll('.hero__copy > *, .chapter__copy > *, .closing > *').forEach((element) => {
      element.classList.add('js-reveal')
      revealObserver.observe(element)
    })

    resize()
    if (reducedMotion) renderStatic()
    else animate()
  } catch (error) {
    console.warn('CareLoop 3D scene unavailable; showing the page without WebGL.', error)
  }
}