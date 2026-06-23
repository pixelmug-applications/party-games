import { createRouter, createWebHashHistory } from 'vue-router';
import LandingView from '../views/LandingView.vue';
import PixelGameView from '../views/PixelGameView.vue';

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'landing', component: LandingView },
    { path: '/games', name: 'games', component: PixelGameView },
  ],
});

export default router;
