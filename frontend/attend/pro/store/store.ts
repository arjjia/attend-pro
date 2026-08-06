namespace $ {

	export type $attend_pro_user = {
		id: string
		email: string
		role: 'student' | 'teacher'
		full_name: string
		group_name: string | null
	}

	export type $attend_pro_lesson = {
		id: string
		course_code: string
		title: string
		kind: string
		group_name: string
		room: string
		starts_at: string
		ends_at: string
		teacher_name: string
		state: 'scheduled' | 'current' | 'ended'
		test_managed: boolean
	}

	export type $attend_pro_device = {
		user_id: string
		device_id: string
		private_key: CryptoKey
		public_jwk: $attend_pro_crypto_jwk
		credential: $attend_pro_crypto_envelope
	}

	export type $attend_pro_permit_bundle = {
		teacher_credential: $attend_pro_crypto_envelope
		permit: $attend_pro_crypto_envelope
	}

	export type $attend_pro_proof = {
		teacher_credential: $attend_pro_crypto_envelope
		permit: $attend_pro_crypto_envelope
		challenge: $attend_pro_crypto_envelope
		student_credential: $attend_pro_crypto_envelope
		claim: $attend_pro_crypto_envelope
		replica_refs?: string[]
	}

	type $attend_pro_db = {
		Meta: { Key: string, Doc: any, Indexes: {} }
		Devices: { Key: string, Doc: $attend_pro_device, Indexes: {} }
		Permits: { Key: string, Doc: $attend_pro_permit_bundle, Indexes: {} }
		Pending: { Key: string, Doc: $attend_pro_proof, Indexes: {} }
		Decisions: { Key: string, Doc: $attend_pro_crypto_envelope, Indexes: {} }
	}

	export class $attend_pro_store extends $mol_object2 {

		@ $mol_mem
		db() {
			return $mol_wire_sync( this as $attend_pro_store ).db_init()
		}

		db_init() {
			return this.$.$mol_db< $attend_pro_db >( 'attend-pro-v1',
				migration => migration.store_make( 'Meta' ),
				migration => migration.store_make( 'Devices' ),
				migration => migration.store_make( 'Permits' ),
				migration => migration.store_make( 'Pending' ),
				migration => migration.store_make( 'Decisions' ),
			)
		}

		async get< Name extends keyof $attend_pro_db >( store: Name, key: string ) {
			return await this.db().read( store )[ store ].get( key ) as $attend_pro_db[ Name ][ 'Doc' ] | undefined
		}

		async put< Name extends keyof $attend_pro_db >(
			store: Name, key: string, value: $attend_pro_db[ Name ][ 'Doc' ],
		) {
			const transaction = this.db().change( store )
			await transaction.stores[ store ].put( value, key )
			await transaction.commit()
			return value
		}

		async drop< Name extends keyof $attend_pro_db >( store: Name, key: string ) {
			const transaction = this.db().change( store )
			await transaction.stores[ store ].drop( key )
			await transaction.commit()
		}

		async all< Name extends keyof $attend_pro_db >( store: Name ) {
			return await this.db().read( store )[ store ].select() as $attend_pro_db[ Name ][ 'Doc' ][]
		}

		async pending_entries() {
			const db = this.db()
			const keys = await new Promise<IDBValidKey[]>( ( done, fail ) => {
				const request = db.native.transaction( 'Pending', 'readonly' ).objectStore( 'Pending' ).getAllKeys()
				request.onsuccess = () => done( request.result )
				request.onerror = () => fail( request.error )
			} )
			const values = await this.all( 'Pending' )
			return values.map( ( proof, index ) => ({ claim_id: String( keys[ index ] ), proof }) )
		}

	}

}
