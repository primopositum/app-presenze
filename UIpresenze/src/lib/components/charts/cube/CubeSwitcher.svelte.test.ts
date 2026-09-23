import { describe, it, expect } from 'vitest';
import { render } from 'vitest-browser-svelte';
import CubeHarness from './__fixtures__/CubeHarness.svelte';

function cubeElement(container: HTMLElement) {
  const cube = container.querySelector<HTMLElement>('.cube');
  if (!cube) throw new Error('Cubo non trovato');
  return cube;
}

function faceElements(container: HTMLElement) {
  return Array.from(container.querySelectorAll<HTMLElement>('.cube-face'));
}

/** Gradi di rotazione letti dallo stile inline del cubo. */
function rotationOf(container: HTMLElement) {
  const transform = cubeElement(container).style.transform;
  const match = transform.match(/rotateY\((-?[\d.]+)deg\)/);
  return match ? Number(match[1]) : NaN;
}

const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => resolve(null)));

/**
 * Attende l'angolo atteso.
 *
 * Il cubo rientra nello spazio 3D un frame prima di girare, quindi subito dopo
 * il click l'angolo e' ancora quello di partenza: senza questa attesa si
 * leggerebbe il fotogramma intermedio.
 */
async function rotatedTo(container: HTMLElement, degrees: number) {
  for (let frame = 0; frame < 12; frame += 1) {
    if (rotationOf(container) === degrees) return;
    await nextFrame();
  }
  throw new Error(`Il cubo non ha raggiunto ${degrees} gradi (ora: ${rotationOf(container)})`);
}

/** Attende che il cubo sia tornato piatto a fine rotazione. */
async function settled(container: HTMLElement) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (cubeElement(container).style.transform === 'none') return;
    await new Promise((resolve) => setTimeout(resolve, 25));
  }
  throw new Error('Il cubo non e tornato piatto');
}

describe('CubeSwitcher a schermo intero', () => {
  it('riporta la pagina dove era prima di ingrandire', async () => {
    const screen = render(CubeHarness, { expandable: true, tall: true });

    // Pagina scrollata in basso con il cubo in vista, come quando l'utente clicca.
    const root = document.querySelector('.cube-switcher') as HTMLElement;
    root.scrollIntoView({ block: 'center' });
    await nextFrame();
    const scrollPrimaDiIngrandire = window.scrollY;
    const altezzaPagina = document.documentElement.scrollHeight;
    expect(scrollPrimaDiIngrandire).toBeGreaterThan(0);

    await screen.getByRole('button', { name: 'Ingrandisci i grafici' }).click();
    await nextFrame();
    // Il cubo esce dal flusso ma lascia il suo ingombro: la pagina non si accorcia.
    expect(root.style.getPropertyValue('--cube-placeholder')).not.toBe('auto');

    await screen.getByRole('button', { name: 'Riduci i grafici' }).click();
    for (let frame = 0; frame < 3; frame += 1) await nextFrame();

    expect(document.body.style.position).toBe('');
    expect(document.documentElement.scrollHeight).toBe(altezzaPagina);
    expect(window.scrollY).toBe(scrollPrimaDiIngrandire);

    window.scrollTo(0, 0);
  });
});

describe('CubeSwitcher con le facce passate come figli', () => {
  it('registra ogni faccia e mostra solo la prima come attiva', async () => {
    const screen = render(CubeHarness);
    const container = screen.container as HTMLElement;

    const faces = faceElements(container);
    expect(faces).toHaveLength(3);
    expect(faces[0].classList.contains('active')).toBe(true);
    expect(faces[1].hasAttribute('inert')).toBe(true);
    await expect.element(screen.getByText('Contenuto C')).toBeInTheDocument();
  });

  it('dispone le facce a 120 gradi l una dall altra mentre gira', async () => {
    const screen = render(CubeHarness);
    const container = screen.container as HTMLElement;

    await screen.getByRole('button', { name: 'Schermata successiva' }).click();
    await rotatedTo(container, -120);

    const faces = faceElements(container);
    expect(faces[0].style.transform).toContain('rotateY(0deg)');
    expect(faces[1].style.transform).toContain('rotateY(120deg)');
    expect(faces[2].style.transform).toContain('rotateY(240deg)');
  });

  it('a rotazione finita esce dal 3D e lascia a schermo solo la faccia attiva', async () => {
    const screen = render(CubeHarness);
    const container = screen.container as HTMLElement;

    // Fermo, il cubo e' piatto: dentro un contesto 3D meta' delle facce non
    // riceverebbe ne' la rotella ne' il passaggio del mouse.
    expect(cubeElement(container).style.transform).toBe('none');
    expect(faceElements(container).map((face) => face.style.transform)).toEqual(['none', 'none', 'none']);

    await screen.getByRole('button', { name: 'Schermata successiva' }).click();
    await settled(container);

    const faces = faceElements(container);
    expect(faces.map((face) => face.style.transform)).toEqual(['none', 'none', 'none']);
    expect(faces.map((face) => face.style.visibility)).toEqual(['hidden', 'visible', 'hidden']);
    expect(faces[1].classList.contains('active')).toBe(true);
  });

  it('usa le etichette delle facce nei tab di navigazione', async () => {
    const screen = render(CubeHarness);

    await expect.element(screen.getByRole('button', { name: 'Prima' })).toBeInTheDocument();
    await expect.element(screen.getByRole('button', { name: 'Terza' })).toBeInTheDocument();
  });

  it('gira in avanti e continua a girare tornando alla prima faccia', async () => {
    const screen = render(CubeHarness);
    const container = screen.container as HTMLElement;
    const next = screen.getByRole('button', { name: 'Schermata successiva' });

    await next.click();
    await rotatedTo(container, -120);
    expect(faceElements(container)[1].classList.contains('active')).toBe(true);
    await settled(container);

    await next.click();
    await rotatedTo(container, -240);
    await settled(container);
    await next.click();
    // Tornati alla prima faccia l angolo non si azzera: il cubo prosegue nello stesso verso.
    await rotatedTo(container, -360);
    expect(faceElements(container)[0].classList.contains('active')).toBe(true);
  });

  it('salta alla faccia scelta dal tab prendendo la strada piu corta', async () => {
    const screen = render(CubeHarness);
    const container = screen.container as HTMLElement;

    await screen.getByRole('button', { name: 'Terza' }).click();
    // Dalla prima alla terza conviene girare indietro di un passo.
    await rotatedTo(container, 120);

    expect(faceElements(container)[2].classList.contains('active')).toBe(true);
  });

  it('senza loop spegne i pulsanti sugli estremi', async () => {
    const screen = render(CubeHarness, { loop: false });

    await expect.element(screen.getByRole('button', { name: 'Schermata precedente' })).toBeDisabled();
    await screen.getByRole('button', { name: 'Terza' }).click();
    await expect.element(screen.getByRole('button', { name: 'Schermata successiva' })).toBeDisabled();
  });
});
