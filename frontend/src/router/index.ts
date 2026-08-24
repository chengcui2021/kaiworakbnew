import { createRouter, createWebHistory } from 'vue-router'
import WorkspacesPage from '../pages/WorkspacesPage.vue'
import WorkspaceDetailPage from '../pages/WorkspaceDetailPage.vue'
import WorkstreamsPage from '../pages/WorkstreamsPage.vue'
import WorkstreamDetailPage from '../pages/WorkstreamDetailPage.vue'
import SearchPage from '../pages/SearchPage.vue'
import ApprovedKnowledgePage from '../pages/ApprovedKnowledgePage.vue'
import ContextPackagesPage from '../pages/ContextPackagesPage.vue'
import MedicalDevicePocPage from '../pages/MedicalDevicePocPage.vue'
import SubmitEntryPage from '../pages/SubmitEntryPage.vue'
import BrowseEntriesPage from '../pages/BrowseEntriesPage.vue'
import TagsPage from '../pages/TagsPage.vue'
import TemplatesPage from '../pages/TemplatesPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/workspaces' },
    {
      path: '/workspaces',
      name: 'workspaces',
      component: WorkspacesPage,
      meta: {
        layout: 'DefaultLayout',
        breadcrumb: [{ label: 'Workspaces', to: null }],
      },
    },
    {
      path: '/workspaces/:id',
      name: 'workspace-detail',
      component: WorkspaceDetailPage,
      props: true,
      meta: {
        layout: 'DefaultLayout',
        // second segment (workspace name) is resolved dynamically in DefaultLayout.vue
        breadcrumb: [{ label: 'Workspaces', to: '/workspaces' }],
      },
    },
    {
      path: '/workstreams',
      name: 'workstreams',
      component: WorkstreamsPage,
      meta: { layout: 'DefaultLayout', breadcrumb: [{ label: 'Workstreams', to: null }] },
    },
    {
      path: '/workstreams/:id',
      name: 'workstream-detail',
      component: WorkstreamDetailPage,
      props: true,
      meta: { layout: 'DefaultLayout', breadcrumb: [{ label: 'Workstreams', to: '/workstreams' }] },
    },
    {
      path: '/approved',
      name: 'approved',
      component: ApprovedKnowledgePage,
      meta: {
        layout: 'DefaultLayout',
        breadcrumb: [{ label: 'Approved Knowledge', to: null }],
      },
    },
    {
      path: '/packages',
      name: 'packages',
      component: ContextPackagesPage,
      meta: {
        layout: 'DefaultLayout',
        breadcrumb: [{ label: 'Context Packages', to: null }],
      },
    },
    {
      path: '/search',
      name: 'search',
      component: SearchPage,
      meta: {
        layout: 'DefaultLayout',
        breadcrumb: [{ label: 'Search', to: null }],
      },
    },
    {
      path: '/submit',
      name: 'submit',
      component: SubmitEntryPage,
      meta: {
        layout: 'DefaultLayout',
        breadcrumb: [{ label: 'Submit Entry', to: null }],
      },
    },
    {
      path: '/browse',
      name: 'browse',
      component: BrowseEntriesPage,
      meta: {
        layout: 'DefaultLayout',
        breadcrumb: [{ label: 'Browse Entries', to: null }],
      },
    },
    {
      path: '/tags',
      name: 'tags',
      component: TagsPage,
      meta: {
        layout: 'DefaultLayout',
        breadcrumb: [{ label: 'Tags', to: null }],
      },
    },
    {
      path: '/templates',
      name: 'templates',
      component: TemplatesPage,
      meta: {
        layout: 'DefaultLayout',
        breadcrumb: [{ label: 'Templates', to: null }],
      },
    },
    {
      path: '/templates/create',
      name: 'create-template',
      component: () => import('../pages/CreateTemplatePage.vue'),
      meta: {
        layout: 'DefaultLayout',
        breadcrumb: [
          { label: 'Templates', to: '/templates' },
          { label: 'Create Template', to: null },
        ],
      },
    },
    {
      path: '/templates/:id/edit',
      name: 'edit-template',
      component: () => import('../pages/EditTemplatePage.vue'),
      props: true,
      meta: {
        layout: 'DefaultLayout',
        breadcrumb: [
          { label: 'Templates', to: '/templates' },
          { label: 'Edit Template', to: null },
        ],
      },
    },
    {
      path: '/entries/:id/edit',
      name: 'edit-entry',
      component: () => import('../pages/EditEntryPage.vue'),
      props: true,
      meta: {
        layout: 'DefaultLayout',
        breadcrumb: [
          { label: 'Browse Entries', to: '/browse' },
          { label: 'Edit Entry', to: null },
        ],
      },
    },
    {
      path: '/medical-device-poc',
      name: 'medical-device-poc',
      component: MedicalDevicePocPage,
      meta: {
        layout: 'DefaultLayout',
        breadcrumb: [{ label: 'Medical Device PoC', to: null }],
      },
    },
  ],
})
