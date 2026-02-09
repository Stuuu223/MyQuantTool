# T+1 Quick Reference Card

## Key Monitoring List
1. **002514.SZ (Baoxin Technology)**
   - **Focus**: Gap up > 1%?
   - **Red Line**: Drop > 4% (triggers rollback)

2. **002054.SZ (Demei Chemical)**
   - **Focus**: Does it hold MA at close?
   - **Risk**: Market cap factor bias risk

3. **002987.SZ (Jingbei Tech)**
   - **Focus**: Trap detection test sample
   - **Validation**: Big rally = trap logic too strict; Big drop = trap logic correct

## Emergency Rollback Plan
If verification fails, execute:
1. `git checkout v9.4.5`
2. Restore Ratio correction factor to 1.0
3. Commit tag `v9.4.7-rollback`
