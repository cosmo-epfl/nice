Now we need to call .transform method with return\_only\_invariants =
False, which is default value:

.. code:: ipython3

    data_even, data_odd, invariants_even = nice[1].transform(train_coefficients[1])

result is data\_even, data\_odd and invariants\_even. First two objects
are covariants, the last is invariants.

There is one another important symmetry in addition to translational and
rotational one. Usually atomic properties, such as energy, transform in
certain way also with respect to inversion. Particularly, energy is
invariant with respect to it.

In NICE features are separated in two groups - the ones which are
invariant with respect to inversion, and the ones which change their
sign. The first are called even, second are called odd.

Now let's take a look at the returned objects more closely:

invariants is the same object as in the previous tutorial - dictionary,
where keys are body order

.. code:: ipython3

    for key in invariants_even.keys():
        print(invariants_even[key].shape)


.. raw:: html
    
    <embed>
    <pre>
    <p style="margin-left: 5%;font-size:12px;line-height: 1.2; overflow:auto" >
        (40000, 10)
        (40000, 200)
        (40000, 200)
        (40000, 200)
    </p>
    </pre>
    </embed>
    
Returned covariants are covariants after last block, i. e. in our case
of body order 4. (functionality to get all covariants of all body order
from StandardSequence will be added in the next version of NICE)

Even covariants are packed in the class Data, which has two relevant
fields - .covariants\_ and .actual\_sizes\_. (getters are also to be
added in the next version) First is np.array with covariants themselves.
It has following indexing -[environmental\_index, feature\_index,
lambda, m]. But the problem is that for each lambda channel actual
number of features is different. Thus, shape of this array doesn't
reflect real number of meaningfull entries. Information about actual
number of features is stored in .actual\_sizes\_:

.. code:: ipython3

    print(type(data_even))
    print("shape of even covariants array: {}".format(data_even.covariants_.shape))
    print("actual sizes of even covariants: {}".format(data_even.actual_sizes_))


.. raw:: html
    
    <embed>
    <pre>
    <p style="margin-left: 5%;font-size:12px;line-height: 1.2; overflow:auto" >
        <class 'nice.nice_utilities.Data'>
        shape of even covariants array: (40000, 87, 6, 11)
        actual sizes of even covariants: [22 55 73 83 87 76]
    </p>
    </pre>
    </embed>
    
The same for odd covariants:

.. code:: ipython3

    print("shape of odd covariants array: {}".format(data_odd.covariants_.shape))
    print("actual sizes of odd covariants: {}".format(data_odd.actual_sizes_))


.. raw:: html
    
    <embed>
    <pre>
    <p style="margin-left: 5%;font-size:12px;line-height: 1.2; overflow:auto" >
        shape of odd covariants array: (40000, 88, 6, 11)
        actual sizes of odd covariants: [20 54 72 87 88 75]
    </p>
    </pre>
    </embed>
    
There is one another point - that for each lambda channel size of
covariant vectors is (2 \* lambda + 1). These vectors are stored from
the beginning. It means that meaningfull entries for each lambda are
located in [:, :, lambda, :(2 \* lambda + 1)]

In the `nice
article <https://aip.scitation.org/doi/10.1063/5.0021116>`__ other
definition of parity is used. Covariants are splitted into true and
pseudo groups. All covariants in true group are transformed with respect
to inversion as (-1)^lambda, while all covariants in the pseudo group
are transformed as (-1) ^ (lambda + 1).

There is special class - ParityDefinitionChanger to switch between these
definitions:

.. code:: ipython3

    data_true, data_pseudo = ParityDefinitionChanger().transform(data_even, data_odd)
    
    print(data_true.covariants_.shape)
    print(data_true.actual_sizes_)
    
    print(data_pseudo.covariants_.shape)
    print(data_pseudo.actual_sizes_)


.. raw:: html
    
    <embed>
    <pre>
    <p style="margin-left: 5%;font-size:12px;line-height: 1.2; overflow:auto" >
        (40000, 87, 6, 11)
        [22 54 73 87 87 75]
        (40000, 88, 6, 11)
        [20 55 72 83 88 76]
    </p>
    </pre>
    </embed>
    
This transformation is symmetric, thus, we can use this it once again to
go back from true and pseudo covariants to even and odd:

.. code:: ipython3

    data_even, data_odd = ParityDefinitionChanger().transform(data_true, data_pseudo)

There is one another discrepancy - covariants defined in the nice
article, are smaller by the factor of (2 \* lambda + 1). Thus, the last
step to get full compliance is the following:

.. code:: ipython3

    for lambd in range(6):
        data_true.covariants_[:, :data_true.actual_sizes_[lambd],
                              lambd, :(2 * lambd + 1)] /= (2 * lambd + 1)
        data_pseudo.covariants_[:, :data_pseudo.actual_sizes_[lambd],
                                lambd, :(2 * lambd + 1)] /= (2 * lambd + 1)
