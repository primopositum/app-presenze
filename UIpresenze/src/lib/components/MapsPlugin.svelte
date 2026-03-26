<script context="module" lang="ts">
  let mapsOptionsConfigured = false;
</script>

<script lang="ts">
  import { importLibrary, setOptions } from '@googlemaps/js-api-loader';
  import { onMount, onDestroy } from 'svelte';

  const startPoint = { name: 'Centro Italia', lat: 42.5, lng: 12.5 };

  let mapContainer: HTMLDivElement;
  let inputA: HTMLInputElement;
  let inputB: HTMLInputElement;
  let map: google.maps.Map;
  let directionsService: google.maps.DirectionsService;
  let directionsRenderer: google.maps.DirectionsRenderer;
  let geocoder: google.maps.Geocoder;
  let autocompleteA: google.maps.places.Autocomplete;
  let autocompleteB: google.maps.places.Autocomplete;

  let address1 = '';
  let address2 = '';
  // Posizioni risolte direttamente dalle Places API (priorità sul geocoder)
  let placeLocationA: google.maps.LatLng | null = null;
  let placeLocationB: google.maps.LatLng | null = null;

  let distance: string | null = null;
  let duration: string | null = null;
  let loading = false;
  let error = '';
  let useAdvancedMarkers = false;
  let mapReady = false;

  const mapsApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY ?? '';
  const googleMapId =
    import.meta.env.VITE_GOOGLE_MAP_ID ?? import.meta.env.PUBLIC_GOOGLE_MAP_ID ?? '';

  onMount(async () => {
    if (!mapsApiKey) {
      error = 'Chiave Google Maps mancante: imposta VITE_GOOGLE_MAPS_API_KEY nel file .env';
      return;
    }

    try {
      if (!mapContainer) {
        error = 'Contenitore mappa non disponibile.';
        return;
      }

      if (!mapsOptionsConfigured) {
        setOptions({
          key: mapsApiKey,
          v: 'weekly',
          // ← 'places' aggiunto qui
          libraries: ['maps', 'geocoding', 'routes', 'marker', 'places'],
          ...(googleMapId ? { mapIds: [googleMapId] } : {}),
          language: 'it',
          region: 'IT'
        });
        mapsOptionsConfigured = true;
      }

      const { Map } = (await importLibrary('maps')) as google.maps.MapsLibrary;
      useAdvancedMarkers = Boolean(googleMapId);

      map = new Map(mapContainer, {
        center: { lat: startPoint.lat, lng: startPoint.lng },
        zoom: 7,
        ...(googleMapId ? { mapId: googleMapId } : {}),
        disableDefaultUI: false,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
        styles: [
          { elementType: 'geometry', stylers: [{ color: '#f5f0e8' }] },
          { elementType: 'labels.text.fill', stylers: [{ color: '#4a4035' }] },
          { elementType: 'labels.text.stroke', stylers: [{ color: '#f5f0e8' }] },
          { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#ffffff' }] },
          { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#e0d8cc' }] },
          { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#b8d4e8' }] },
          { featureType: 'poi', elementType: 'geometry', stylers: [{ color: '#ddd5c5' }] },
          { featureType: 'poi.park', elementType: 'geometry', stylers: [{ color: '#c8dbb0' }] },
          { featureType: 'administrative', elementType: 'geometry.stroke', stylers: [{ color: '#c9b99a' }] },
          { featureType: 'transit', stylers: [{ visibility: 'off' }] }
        ]
      });

      const { DirectionsService, DirectionsRenderer } =
        (await importLibrary('routes')) as google.maps.RoutesLibrary;
      const { Geocoder } = (await importLibrary('geocoding')) as google.maps.GeocodingLibrary;

      directionsService = new DirectionsService();
      geocoder = new Geocoder();

      directionsRenderer = new DirectionsRenderer({
        suppressMarkers: true,
        polylineOptions: {
          strokeColor: '#264653',
          strokeWeight: 4,
          strokeOpacity: 0.85
        }
      });
      directionsRenderer.setMap(map);

      // ── Places Autocomplete ──────────────────────────────────────────────
      await importLibrary('places');

      const autocompleteOptions: google.maps.places.AutocompleteOptions = {
        // Nessun filtro su 'types' → restituisce anche stadi, aziende, POI, ecc.
        fields: ['geometry', 'name', 'formatted_address'],
        // Leggero bias verso l'Italia senza escludere il resto
        componentRestrictions: { country: [] } // [] = mondiale; metti ['it'] per limitare all'Italia
      };

      autocompleteA = new google.maps.places.Autocomplete(inputA, autocompleteOptions);
      autocompleteB = new google.maps.places.Autocomplete(inputB, autocompleteOptions);

      // Quando l'utente seleziona un suggerimento salviamo la location precisa
      autocompleteA.addListener('place_changed', () => {
        const place = autocompleteA.getPlace();
        placeLocationA = place.geometry?.location ?? null;
        if (place.name) address1 = place.formatted_address ?? place.name;
      });

      autocompleteB.addListener('place_changed', () => {
        const place = autocompleteB.getPlace();
        placeLocationB = place.geometry?.location ?? null;
        if (place.name) address2 = place.formatted_address ?? place.name;
      });
      // ────────────────────────────────────────────────────────────────────

      if (useAdvancedMarkers) {
        const { AdvancedMarkerElement } = (await importLibrary('marker')) as google.maps.MarkerLibrary;
        const pin = document.createElement('div');
        pin.className = 'city-pin';
        pin.textContent = startPoint.name;
        new AdvancedMarkerElement({
          map,
          position: { lat: startPoint.lat, lng: startPoint.lng },
          content: pin
        });
      } else {
        new google.maps.Marker({
          map,
          position: { lat: startPoint.lat, lng: startPoint.lng },
          title: startPoint.name,
          label: startPoint.name.charAt(0)
        });
      }

      mapReady = true;
      error = '';
    } catch (e: unknown) {
      mapReady = false;
      error = e instanceof Error ? e.message : 'Errore inizializzazione Google Maps';
    }
  });

  onDestroy(() => {
    if (directionsRenderer) directionsRenderer.setMap(null);
  });

  /** Geocoder usato solo come fallback se l'utente non seleziona dal menu Places */
  function geocodeAddress(address: string): Promise<google.maps.LatLng> {
    return new Promise((resolve, reject) => {
      geocoder.geocode({ address, region: 'IT' }, (results, status) => {
        if (status === 'OK' && results && results[0]) {
          resolve(results[0].geometry.location);
        } else {
          reject(new Error(`Indirizzo non trovato: "${address}"`));
        }
      });
    });
  }

  async function createMarker(position: google.maps.LatLng, label: string, color: string) {
    if (useAdvancedMarkers) {
      const { AdvancedMarkerElement } = (await importLibrary('marker')) as google.maps.MarkerLibrary;
      const el = document.createElement('div');
      el.className = 'marker-bubble';
      el.style.background = color;
      el.textContent = label;
      return new AdvancedMarkerElement({ map, position, content: el });
    }
    return new google.maps.Marker({
      map,
      position,
      label,
      title: `Punto ${label}`,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        fillColor: color,
        fillOpacity: 1,
        strokeColor: '#ffffff',
        strokeWeight: 2,
        scale: 9
      }
    });
  }

  let markerA: google.maps.marker.AdvancedMarkerElement | google.maps.Marker | null = null;
  let markerB: google.maps.marker.AdvancedMarkerElement | google.maps.Marker | null = null;

  function clearMarker(
    marker: google.maps.marker.AdvancedMarkerElement | google.maps.Marker | null
  ) {
    if (!marker) return;
    if ('setMap' in marker) { marker.setMap(null); return; }
    marker.map = null;
  }

  export async function calcolaDistanza(a1?: string, a2?: string): Promise<number | null> {
    if (a1 !== undefined) { address1 = a1; placeLocationA = null; }
    if (a2 !== undefined) { address2 = a2; placeLocationB = null; }

    if (!mapReady || !directionsRenderer || !directionsService || !geocoder) {
      error = 'Mappa in inizializzazione, riprova tra un istante.';
      return null;
    }
    if (!address1.trim() || !address2.trim()) {
      error = 'Inserisci entrambi gli indirizzi.';
      return null;
    }

    loading = true;
    error = '';
    distance = null;
    duration = null;

    if (markerA) { clearMarker(markerA); markerA = null; }
    if (markerB) { clearMarker(markerB); markerB = null; }
    directionsRenderer.setDirections({ routes: [] } as any);

    try {
      // Usa la location Places se disponibile, altrimenti cade sul geocoder
      const [locA, locB] = await Promise.all([
        placeLocationA ? Promise.resolve(placeLocationA) : geocodeAddress(address1),
        placeLocationB ? Promise.resolve(placeLocationB) : geocodeAddress(address2)
      ]);

      const km = await new Promise<number | null>((resolve) => {
        directionsService.route(
          { origin: locA, destination: locB, travelMode: google.maps.TravelMode.DRIVING },
          async (result, status) => {
            if (status === 'OK' && result) {
              directionsRenderer.setDirections(result);
              const leg = result.routes[0].legs[0];
              distance = leg.distance?.text ?? null;
              duration = leg.duration?.text ?? null;
              markerA = await createMarker(leg.start_location, 'A', '#e63946');
              markerB = await createMarker(leg.end_location, 'B', '#2a9d8f');
              const meters = leg.distance?.value;
              resolve(typeof meters === 'number' ? meters / 1000 : null);
            } else {
              error = 'Impossibile calcolare il percorso tra questi due punti.';
              resolve(null);
            }
            loading = false;
          }
        );
      });

      return km;
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Errore sconosciuto';
      loading = false;
      return null;
    }
  }

  // Reset della location salvata se l'utente modifica manualmente il testo
  function onInput(field: 'A' | 'B') {
    if (field === 'A') placeLocationA = null;
    else placeLocationB = null;
  }
</script>

<div class="wrapper">
  <div class="panel">
    <div class="panel-header">
      <div class="logo">Map</div>
      <div>
        <h1>Distanza su Strada</h1>
        <p class="subtitle">Partenza da <strong>{startPoint.name}</strong></p>
      </div>
    </div>

    <div class="field">
      <label for="addr1">Punto A</label>
      <input
        id="addr1"
        bind:this={inputA}
        type="text"
        bind:value={address1}
        placeholder="es. Stadio di Bergamo"
        on:input={() => onInput('A')}
        on:keydown={(e) => e.key === 'Enter' && calcolaDistanza()}
      />
    </div>

    <div class="field">
      <label for="addr2">Punto B</label>
      <input
        id="addr2"
        bind:this={inputB}
        type="text"
        bind:value={address2}
        placeholder="es. Colosseo, Roma"
        on:input={() => onInput('B')}
        on:keydown={(e) => e.key === 'Enter' && calcolaDistanza()}
      />
    </div>

    <button class="btn" on:click={() => calcolaDistanza()} disabled={loading}>
      {#if loading}
        <span class="spinner"></span> Calcolo percorso...
      {:else}
        Calcola Percorso →
      {/if}
    </button>

    {#if error}
      <div class="error">ATTENZIONE: {error}</div>
    {/if}

    {#if distance !== null && duration !== null}
      <div class="result">
        <div class="result-row">
          <div class="result-block">
            <div class="result-label">Distanza</div>
            <div class="result-value">{distance}</div>
          </div>
          <div class="divider"></div>
          <div class="result-block">
            <div class="result-label">Tempo stimato</div>
            <div class="result-value">{duration}</div>
          </div>
        </div>
        <div class="result-note">calcolata su strade reali via Google Maps</div>
      </div>
    {/if}
  </div>

  <div class="map-wrap">
    <div bind:this={mapContainer} class="map"></div>
    {#if error}
      <div class="map-error">{error}</div>
    {/if}
  </div>
</div>


<style>
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,300;0,600;1,300&family=DM+Sans:wght@400;500&display=swap');

  .wrapper,
  .wrapper * {
    box-sizing: border-box;
  }

  .wrapper {
    display: flex;
    height: 100vh;
    font-family: 'DM Sans', sans-serif;
  }

  .panel {
    width: 340px;
    flex-shrink: 0;
    background: #1a1a2e;
    color: #e8e0d4;
    padding: 32px 28px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    overflow-y: auto;
    z-index: 10;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.3);
  }

  .panel-header {
    display: flex;
    align-items: center;
    gap: 14px;
    padding-bottom: 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }

  .logo {
    font-size: 1rem;
    line-height: 1;
    font-weight: 700;
    letter-spacing: 0.03em;
  }

  h1 {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 1.25rem;
    color: #f0e6d3;
    line-height: 1.2;
  }

  .subtitle {
    font-size: 0.8rem;
    color: #9e9aac;
    margin-top: 3px;
  }

  .subtitle strong {
    color: #c9b99a;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 7px;
  }

  label {
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #9e9aac;
  }

  input {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    padding: 11px 14px;
    color: #f0e6d3;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.9rem;
    outline: none;
    transition: border-color 0.2s, background 0.2s;
  }

  input::placeholder {
    color: #5e5a6e;
  }

  input:focus {
    border-color: #c9b99a;
    background: rgba(255, 255, 255, 0.09);
  }

  .btn {
    background: #c9b99a;
    color: #1a1a2e;
    border: none;
    border-radius: 8px;
    padding: 13px 20px;
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    font-size: 0.95rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    transition: background 0.2s, transform 0.1s;
  }

  .btn:hover:not(:disabled) {
    background: #ddd0b8;
    transform: translateY(-1px);
  }

  .btn:active:not(:disabled) {
    transform: translateY(0);
  }

  .btn:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .spinner {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(26, 26, 46, 0.3);
    border-top-color: #1a1a2e;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    display: inline-block;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .error {
    background: rgba(230, 57, 70, 0.15);
    border: 1px solid rgba(230, 57, 70, 0.35);
    color: #f18b93;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.85rem;
  }

  .result {
    background: rgba(201, 185, 154, 0.1);
    border: 1px solid rgba(201, 185, 154, 0.3);
    border-radius: 12px;
    padding: 20px;
    animation: fadeUp 0.4s ease;
  }

  .result-row {
    display: flex;
    align-items: center;
  }

  .result-block {
    flex: 1;
    text-align: center;
  }

  .divider {
    width: 1px;
    height: 48px;
    background: rgba(201, 185, 154, 0.25);
  }

  .result-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #9e9aac;
    margin-bottom: 6px;
  }

  .result-value {
    font-family: 'Fraunces', serif;
    font-size: 1.6rem;
    font-weight: 600;
    color: #c9b99a;
    line-height: 1.1;
  }

  .result-note {
    font-size: 0.7rem;
    color: #5e5a6e;
    margin-top: 12px;
    text-align: center;
  }

  @keyframes fadeUp {
    from {
      opacity: 0;
      transform: translateY(8px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .map-wrap {
    flex: 1;
    position: relative;
  }

  .map {
    width: 100%;
    height: 100%;
  }

  .map-error {
    position: absolute;
    left: 12px;
    right: 12px;
    bottom: 12px;
    z-index: 20;
    background: rgba(153, 27, 27, 0.92);
    color: #ffffff;
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 0.8rem;
    line-height: 1.25;
  }

  :global(.marker-bubble) {
    width: 32px;
    height: 32px;
    border-radius: 50% 50% 50% 0;
    transform: rotate(-45deg);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 700;
    font-size: 0.85rem;
    font-family: 'DM Sans', sans-serif;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  }

  :global(.city-pin) {
    background: #1a1a2e;
    color: #c9b99a;
    padding: 6px 12px;
    border-radius: 20px;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.8rem;
    font-weight: 500;
    white-space: nowrap;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
    border: 1px solid rgba(201, 185, 154, 0.4);
  }

  @media (max-width: 640px) {
    .wrapper {
      flex-direction: column;
    }

    .panel {
      width: 100%;
      height: auto;
    }

    .map-wrap {
      flex: 1;
      min-height: 300px;
    }
  }
</style>
