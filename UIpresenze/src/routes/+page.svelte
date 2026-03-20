<script lang="ts">
  import { goto } from '$app/navigation';
  import CardImage from '$lib/components/CardImage.svelte';
  import IconLinkBar from '$lib/components/IconLinkBar.svelte';
  import { auth } from '$lib/stores/auth';

  let user: any = null;
  let token: string | null = null;
  $: user = $auth.user;
  $: token = $auth.token;
  
   const redirect = (route : string) => {
    if (user?.is_superuser){goto(`/preMenu`, {state : {route}});}
    else{goto(`/${route}`, {state : {route}});}
  }
  function toLogin(){ goto('/login'); }
</script>


<main class="flex flex-col justify-center items-center max-w-3xl mx-auto">
<img src="/logo2.png" alt="logo1" class="justify-center">
{#if token}
  <p  class="font-infinity tracking-[3px]">Buongiorno, {user?.nome}</p>
{:else}
  <p>Non sei autenticato.</p>
  <button onclick={toLogin}>Vai al login</button>
{/if}

<div class="w-full flex justify-center gap-4 p-4">
  <CardImage
    caption="Accedi all'area delle trasferte"
    alt="trasferte"
    on:click = {()=>{goto('/trasferte')}}
    imageSrc="/trasferte.png"
       />
  <CardImage
    caption="Accedi all'area delle presenze"
    alt="presenze"
    on:click = {()=>{redirect('presences')}}
    imageSrc="/presence.png"
     />
</div>
<div >
  <IconLinkBar></IconLinkBar>
</div>
</main>

