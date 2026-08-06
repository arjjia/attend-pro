namespace $ {

	/**
	 * Secondary evidence replica backed by Giper Baza.
	 *
	 * AttendPro signatures remain self-contained and independently verifiable.
	 * Giper contributes an encrypted, signed, convergent local Land that can be
	 * synchronized with a relay later without changing the attendance protocol.
	 */
	export class $attend_pro_giper extends $mol_object2 {

		@ $mol_mem
		land() {
			const stored = this.$.$mol_state_local.value( 'attendpro.giper.private-land' ) as string | null
			if( stored ) return this.$.$giper_baza_glob.Land( new this.$.$giper_baza_link( stored ) )

			// No anonymous reads: Giper encrypts this Land and only the current Lord is King.
			const land = this.$.$giper_baza_glob.land_grab([
				[ null, this.$.$giper_baza_rank_deny ],
			])
			this.$.$mol_state_local.value( 'attendpro.giper.private-land', land.link().str )
			return land
		}

		publish( proof: $attend_pro_proof ) {
			const claim_id = String( proof.claim.payload.claim_id )
			const record = this.$.$attend_pro_crypto_canonical({
				version: 'attendpro.giper-evidence.v1',
				claim_id,
				proof,
			})
			const land = this.land()
			land.Data( this.$.$giper_baza_list_str ).add( record )
			land.units_saving()
			return `giper://${ land.link().str }/${ claim_id }`
		}

	}

}
