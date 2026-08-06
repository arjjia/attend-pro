namespace $ {

	export type $attend_pro_crypto_jwk = JsonWebKey & {
		kty: 'EC'
		crv: 'P-256'
		x: string
		y: string
	}

	export type $attend_pro_crypto_envelope = {
		payload: Record<string, any>
		signature: string
		key_id: string
		algorithm: 'ES256'
	}

	export function $attend_pro_crypto_canonical( value: any ): string {
		if( value === null || typeof value === 'boolean' || typeof value === 'string' ) {
			return JSON.stringify( value )
		}
		if( typeof value === 'number' ) {
			if( !Number.isFinite( value ) ) throw new Error( 'Неконечные числа нельзя подписывать' )
			return JSON.stringify( value )
		}
		if( Array.isArray( value ) ) {
			return '[' + value.map( item => $attend_pro_crypto_canonical( item ) ).join( ',' ) + ']'
		}
		if( typeof value === 'object' ) {
			return '{' + Object.keys( value ).sort().map( key =>
				JSON.stringify( key ) + ':' + $attend_pro_crypto_canonical( value[ key ] )
			).join( ',' ) + '}'
		}
		throw new Error( `Неподдерживаемое значение в подписываемом JSON: ${ typeof value }` )
	}

	export function $attend_pro_crypto_bytes( value: any ) {
		return new TextEncoder().encode( $attend_pro_crypto_canonical( value ) )
	}

	export function $attend_pro_crypto_b64url( bytes: Uint8Array ) {
		let binary = ''
		for( const byte of bytes ) binary += String.fromCharCode( byte )
		return btoa( binary ).replace( /\+/g, '-' ).replace( /\//g, '_' ).replace( /=+$/, '' )
	}

	export function $attend_pro_crypto_b64url_decode( value: string ) {
		const binary = atob( value.replace( /-/g, '+' ).replace( /_/g, '/' ) + '='.repeat( ( 4 - value.length % 4 ) % 4 ) )
		return Uint8Array.from( binary, symbol => symbol.charCodeAt( 0 ) )
	}

	export async function $attend_pro_crypto_digest( value: any ) {
		return $attend_pro_crypto_b64url( new Uint8Array(
			await crypto.subtle.digest( 'SHA-256', $attend_pro_crypto_bytes( value ) )
		) )
	}

	export async function $attend_pro_crypto_key_pair() {
		const pair = await crypto.subtle.generateKey(
			{ name: 'ECDSA', namedCurve: 'P-256' },
			false,
			[ 'sign', 'verify' ],
		) as CryptoKeyPair
		const public_jwk = await crypto.subtle.exportKey( 'jwk', pair.publicKey ) as $attend_pro_crypto_jwk
		return { private_key: pair.privateKey, public_jwk }
	}

	export async function $attend_pro_crypto_sign( private_key: CryptoKey, payload: any ) {
		const signature = await crypto.subtle.sign(
			{ name: 'ECDSA', hash: 'SHA-256' },
			private_key,
			$attend_pro_crypto_bytes( payload ),
		)
		return $attend_pro_crypto_b64url( new Uint8Array( signature ) )
	}

	export async function $attend_pro_crypto_verify(
		public_jwk: JsonWebKey,
		payload: any,
		signature: string,
	) {
		try {
			const key = await crypto.subtle.importKey(
				'jwk', public_jwk, { name: 'ECDSA', namedCurve: 'P-256' }, false, [ 'verify' ],
			)
			return await crypto.subtle.verify(
				{ name: 'ECDSA', hash: 'SHA-256' },
				key,
				$attend_pro_crypto_b64url_decode( signature ),
				$attend_pro_crypto_bytes( payload ),
			)
		} catch( _error ) {
			return false
		}
	}

}
