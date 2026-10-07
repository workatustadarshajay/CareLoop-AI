import { useEffect, useRef } from 'react'
import type * as THREE from 'three'

export function HeroScene() {
  const hostRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const host = hostRef.current
    if (!host) return

    let disposed = false
    let frameId = 0
    let renderer: THREE.WebGLRenderer | undefined
    let scene: THREE.Scene | undefined
    let camera: THREE.PerspectiveCamera | undefined
    let resizeObserver: ResizeObserver | undefined
    let intersectionObserver: IntersectionObserver | undefined
    let visible = true
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    void import('three').then((THREE) => {
      if (disposed) return

      scene = new THREE.Scene()
      camera = new THREE.PerspectiveCamera(36, 1, 0.1, 50)
      camera.position.set(0, 0, 8)
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: false,
        powerPreference: 'low-power',
      })
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
      renderer.setClearColor(0x000000, 0)
      renderer.outputColorSpace = THREE.SRGBColorSpace
      renderer.domElement.setAttribute('aria-hidden', 'true')
      host.append(renderer.domElement)

      scene.add(new THREE.HemisphereLight(0xe8fff6, 0x466e63, 2.1))
      const keyLight = new THREE.DirectionalLight(0xffffff, 2.8)
      keyLight.position.set(-3, 4, 6)
      scene.add(keyLight)

      const orbit = new THREE.Group()
      scene.add(orbit)

      const glass = new THREE.Mesh(
        new THREE.SphereGeometry(0.66, 32, 24),
        new THREE.MeshPhysicalMaterial({
          color: 0x8bcbbb,
          metalness: 0.16,
          roughness: 0.22,
          clearcoat: 0.9,
          transparent: true,
          opacity: 0.62,
        }),
      )
      orbit.add(glass)

      const crossMaterial = new THREE.MeshStandardMaterial({ color: 0xf4f7f3, roughness: 0.3 })
      const crossVertical = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.56, 0.13), crossMaterial)
      const crossHorizontal = new THREE.Mesh(new THREE.BoxGeometry(0.56, 0.16, 0.13), crossMaterial)
      crossVertical.position.z = 0.56
      crossHorizontal.position.z = 0.56
      orbit.add(crossVertical, crossHorizontal)

      const ringMaterials = [
        new THREE.MeshBasicMaterial({ color: 0x0c806d, transparent: true, opacity: 0.54 }),
        new THREE.MeshBasicMaterial({ color: 0x78b6a5, transparent: true, opacity: 0.46 }),
        new THREE.MeshBasicMaterial({ color: 0xcf7c31, transparent: true, opacity: 0.5 }),
      ]
      const rings = ringMaterials.map((material, index) => {
        const ring = new THREE.Mesh(new THREE.TorusGeometry(1.13 + index * 0.35, 0.018, 8, 120), material)
        ring.rotation.set(0.72 + index * 0.48, index * 0.35, index * 0.74)
        orbit.add(ring)
        return ring
      })

      const nodeGeometry = new THREE.SphereGeometry(0.095, 16, 12)
      const nodeMaterials = [
        new THREE.MeshStandardMaterial({ color: 0x0c806d, emissive: 0x0c806d, emissiveIntensity: 0.25 }),
        new THREE.MeshStandardMaterial({ color: 0xcf7c31, emissive: 0xcf7c31, emissiveIntensity: 0.2 }),
        new THREE.MeshStandardMaterial({ color: 0x7196c6, emissive: 0x7196c6, emissiveIntensity: 0.2 }),
      ]
      const nodes = [
        new THREE.Vector3(-1.62, 0.48, 0.15),
        new THREE.Vector3(1.35, 0.96, -0.18),
        new THREE.Vector3(1.04, -1.14, 0.25),
      ]
      const curve = new THREE.CatmullRomCurve3([
        nodes[0],
        new THREE.Vector3(-0.55, 0.8, 0.08),
        nodes[1],
        new THREE.Vector3(1.42, -0.2, 0.06),
        nodes[2],
        new THREE.Vector3(-0.42, -0.82, -0.1),
        nodes[0],
      ])
      const path = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(curve.getPoints(100)),
        new THREE.LineBasicMaterial({ color: 0x0c806d, transparent: true, opacity: 0.24 }),
      )
      orbit.add(path)

      const nodeMeshes = nodes.map((position, index) => {
        const node = new THREE.Mesh(nodeGeometry, nodeMaterials[index])
        node.position.copy(position)
        orbit.add(node)
        return node
      })

      const tileGeometry = new THREE.BoxGeometry(0.52, 0.36, 0.08)
      const tileMaterials = [
        new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.35, metalness: 0.04 }),
        new THREE.MeshStandardMaterial({ color: 0xf3c79b, roughness: 0.4, metalness: 0.02 }),
      ]
      const tiles = [
        { position: new THREE.Vector3(-1.3, -0.32, 0.62), rotation: -0.2 },
        { position: new THREE.Vector3(1.58, 0.18, -0.34), rotation: 0.22 },
      ].map(({ position, rotation }, index) => {
        const tile = new THREE.Mesh(tileGeometry, tileMaterials[index])
        tile.position.copy(position)
        tile.rotation.z = rotation
        tile.userData.baseY = position.y
        orbit.add(tile)
        return tile
      })

      const resize = () => {
        if (!renderer || !camera || !scene) return
        const width = host.clientWidth
        const height = host.clientHeight
        if (!width || !height) return
        camera.aspect = width / height
        camera.updateProjectionMatrix()
        renderer.setSize(width, height, false)
        orbit.position.x = width / height > 1 ? Math.min((width / height) * 1.15, 2.6) : 0.15
        if (reducedMotion) renderer.render(scene, camera)
      }

      const draw = (time: number) => {
        if (disposed || !renderer || !scene || !camera) return
        const seconds = time * 0.001
        if (!reducedMotion) {
          orbit.rotation.y = Math.sin(seconds * 0.28) * 0.12
          orbit.rotation.z = Math.sin(seconds * 0.2) * 0.045
          glass.rotation.y = seconds * 0.12
          rings[0].rotation.z += 0.0018
          rings[1].rotation.x -= 0.0012
          rings[2].rotation.y += 0.0015
          nodeMeshes.forEach((node, index) => {
            node.scale.setScalar(1 + Math.sin(seconds * 1.5 + index) * 0.12)
          })
          tiles.forEach((tile, index) => {
            tile.position.y = tile.userData.baseY + Math.sin(seconds * 1.1 + index * 2) * 0.08
            tile.rotation.y = Math.sin(seconds * 0.55 + index) * 0.16
          })
        }
        renderer.render(scene, camera)
        if (!reducedMotion && visible) frameId = window.requestAnimationFrame(draw)
      }

      resize()
      resizeObserver = new ResizeObserver(resize)
      resizeObserver.observe(host)
      intersectionObserver = new IntersectionObserver(([entry]) => {
        visible = entry.isIntersecting
        if (!visible && frameId) {
          window.cancelAnimationFrame(frameId)
          frameId = 0
        } else if (visible && !reducedMotion && !frameId) {
          frameId = window.requestAnimationFrame(draw)
        }
      })
      intersectionObserver.observe(host)

      if (reducedMotion) draw(0)
      else frameId = window.requestAnimationFrame(draw)
    }).catch(() => {
      host.classList.add('lhero__scene--unavailable')
    })

    return () => {
      disposed = true
      window.cancelAnimationFrame(frameId)
      resizeObserver?.disconnect()
      intersectionObserver?.disconnect()
      scene?.traverse((object) => {
        if ('geometry' in object) (object as THREE.Mesh).geometry.dispose()
        if ('material' in object) {
          const material = (object as THREE.Mesh).material
          if (Array.isArray(material)) material.forEach((item) => item.dispose())
          else material.dispose()
        }
      })
      renderer?.dispose()
      renderer?.domElement.remove()
    }
  }, [])

  return <div className="lhero__scene" ref={hostRef} aria-hidden="true" />
}