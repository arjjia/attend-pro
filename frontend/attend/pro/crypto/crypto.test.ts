namespace $ {

	$mol_test({

		'canonical JSON has deterministic property order'() {
			$mol_assert_equal(
				$attend_pro_crypto_canonical({ z: 1, a: { 'я': true, b: [ 3, 2, 1 ] } }),
				'{"a":{"b":[3,2,1],"я":true},"z":1}',
			)
		},

		async 'device key signs ES256 and private key stays non-extractable'() {
			const pair = await $attend_pro_crypto_key_pair()
			const payload = { version: 'test.v1', message: 'подписано' }
			const signature = await $attend_pro_crypto_sign( pair.private_key, payload )
			$mol_assert_equal( pair.private_key.extractable, false )
			$mol_assert_equal( signature.length, 86 )
			$mol_assert_ok( await $attend_pro_crypto_verify( pair.public_jwk, payload, signature ) )
			$mol_assert_not( await $attend_pro_crypto_verify( pair.public_jwk, { ...payload, message: 'подменено' }, signature ) )
		},

	})

}
