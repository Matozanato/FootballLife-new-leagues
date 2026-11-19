/* Fixed 1v4 / 2v3 draw, using the same slot, fixture and menu list as cup_draw. */
static void state_seed(uint16_t id)
{
  const struct state_ids* state=state_for(id);
  if (!state || id!=state->final) return;
  unsigned char* reg=get_rec(id);
  unsigned char* round=ko_round(id,STATE_OPENING_ROUND);
  if (!reg || rec_count(reg)!=4 || ko_slots(round)!=2) return;
  const int ranks[]={1,4,2,3};
  uint32_t old[4], want[4], list[4];
  unsigned char* match[2];
  for (int i=0;i<2;i++) {
    uint32_t* slot=ko_slot(round,i);
    match[i]=ko_match(*(uint16_t*)(slot+2));
    if (!match[i] || *(uint16_t*)(match[i]+4)!=id ||
        (match[i][6]&63)!=STATE_OPENING_ROUND || (match[i][7]&0x40)) return;
    for (int side=0;side<2;side++) {
      int k=2*i+side;
      const char* how="";
      old[k]=*(uint32_t*)(match[i]+0x14+side*4);
      want[k]=canon_club(cwc_club(state->a1,ranks[k],&how));
    }
  }
  if (!state_field(state,want,4) || !memcmp(old,want,sizeof old)) return;
  unsigned used=0;
  for (int i=0;i<4;i++) {
    int j=0;
    while (j<4 && !same_club(rec_clubs(reg)[i],old[j])) j++;
    if (j==4 || (used&(1u<<j)) || !has_club(want,4,old[j])) return;
    used|=1u<<j;
    list[i]=want[j];
  }
  for (int i=0;i<2;i++) {
    memcpy(ko_slot(round,i),want+2*i,2*sizeof(uint32_t));
    memcpy(match[i]+0x14,want+2*i,2*sizeof(uint32_t));
  }
  memcpy(rec_clubs(reg),list,sizeof list);
  sched_rebuild("Estadual R7: 1v4, 2v3");
}
