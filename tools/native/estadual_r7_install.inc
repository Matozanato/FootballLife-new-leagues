  /* FL26's single-match query. The original handles every other competition and round. */
  static const unsigned char single_sig[]={0x48,0x89,0x5c,0x24,8,0x48,0x89,0x6c,0x24,16,0x48,0x89,0x74,0x24,24};
  if (hook((unsigned char*)(uintptr_t)(exe_base+0x151d1e0), single_sig, sizeof single_sig,
           (void*)state_single_round,&state_single_original)) return 96;
  logf("Estaduais R7 -- chave unica: semifinal simples, final dupla");
