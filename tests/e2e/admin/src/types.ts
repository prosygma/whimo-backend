export type AdminModel = {
  app_label: string;
  model_name: string;
  label: string;
  verbose_name: string;
  admin_class: string;
  count: number;
  sample_pks: string[];
  urls: {
    changelist: string | null;
    add: string | null;
    change: string | null;
    history: string | null;
    delete: string | null;
    autocomplete: string | null;
  };
  permissions: { add: boolean; change: boolean; delete: boolean; view: boolean };
  search_fields: string[];
  list_filter: string[];
  list_display: string[];
  list_filter_submit: boolean;
  autocomplete_fields: string[];
  readonly_fields: string[];
  inlines: string[];
  actions_detail: string[];
  actions_row: string[];
  changelist_actions: string[];
};

export type AdminInventory = {
  admin_index: string;
  login: string;
  logout: string;
  password_change: string;
  jsi18n: string;
  app_list: string[];
  models: AdminModel[];
};

/** One row of the coverage ledger: what happened when we opened a URL. */
export type VisitRecord = {
  url: string;
  status: number | null;
  ok: boolean;
  source: string;
  title?: string;
  djangoError?: string;
  consoleErrors: string[];
  failedRequests: string[];
  badSubresources: string[];
  notes?: string[];
};
